"""Modelli unsupervised sulle caratteristiche della FASE 2: Isolation Forest e Local Outlier Factor.

I due metodi guardano cose diverse: Isolation Forest isola i punti con pochi tagli casuali
(anomalie globali, valori estremi in poche caratteristiche), LOF confronta la densità locale di
un punto con quella dei vicini (anomalie locali, combinazioni insolite di valori non estremi).

Gli ingressi sono relativi al rumore: le ampiezze sono in unità del rumore punto-punto
(`p2p_std`), quindi una stella debole che è solo rumore coincide con una brillante che è solo
rumore. Senza questo i modelli indicherebbero come anomale le stelle deboli, che hanno flusso
relativo con dispersione fino a ~1 (README, FASE 2).
"""
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler


def design_matrix(f: pd.DataFrame) -> pd.DataFrame:
    """Ingressi dei modelli, uno per colonna, tutti adimensionali o in unità di rumore."""
    u = f.p2p_std.clip(lower=1e-12)
    lg = lambda x: np.log10(np.clip(x, 1e-12, None))
    return pd.DataFrame({
        "log_noise_ratio": lg(f.noise_ratio),           # dispersione / errore atteso
        "log_std_p2p": lg(f["std"] / u),                # variabilità oltre il rumore bianco
        "log_amp90_p2p": lg(f.amp_90 / u),
        "log_tail": lg(f.amp_98 / f.amp_90.clip(lower=1e-12)),  # code pesanti rispetto al corpo
        "asinh_skew": np.arcsinh(f["skew"]),
        "asinh_kurt": np.arcsinh(f["kurt"]),
        "log_eta": lg(f.eta),
        "log_ls_period": lg(f.ls_period),
        "ls_power": f.ls_power,
        "log_ls_amp_p2p": lg(f.ls_amp / u),
        "log_bls_period": lg(f.bls_period),
        "log_bls_snr": lg(f.bls_snr),
        "log_bls_duration_h": lg(f.bls_duration_h),
        "log1p_n_dips": np.log1p(f.n_dips),
        "log1p_dip_snr": np.log1p(f.dip_snr),
        "log1p_dip_duration_h": np.log1p(f.dip_duration_h),
        "log1p_n_flares": np.log1p(f.n_flares),
        "log1p_flare_snr": np.log1p(f.flare_snr),
        "log1p_flare_duration_h": np.log1p(f.flare_duration_h),
    }, index=f.index)


def scale(x: pd.DataFrame) -> pd.DataFrame:
    """Mediana a 0 e scarto interquartile a 1, colonna per colonna: robusto alle code."""
    return pd.DataFrame(RobustScaler().fit_transform(x), index=x.index, columns=x.columns)


def isolation_forest(z: pd.DataFrame, n_estimators: int, max_samples: int, seed: int) -> np.ndarray:
    m = IsolationForest(n_estimators=n_estimators, max_samples=min(max_samples, len(z)), random_state=seed)
    return -m.fit(z).score_samples(z)  # più alto = più anomalo


def lof(z: pd.DataFrame, n_neighbors: int) -> np.ndarray:
    m = LocalOutlierFactor(n_neighbors=min(n_neighbors, len(z) - 1))
    m.fit(z)
    return -m.negative_outlier_factor_  # ~1 per un punto tipico, > 1 = densità più bassa dei vicini


def percentile_rank(score: np.ndarray) -> np.ndarray:
    """Rango in (0, 1]: 1 = il più anomalo."""
    return rankdata(score) / len(score)


def drivers(z: pd.DataFrame, n: int = 3) -> list[str]:
    """Le n caratteristiche più lontane dalla mediana per ogni stella, per leggere il perché."""
    a = z.abs().to_numpy()
    top = np.argsort(-a, axis=1)[:, :n]
    cols = z.columns.to_numpy()
    return [", ".join(f"{cols[j]}={z.iat[i, j]:+.1f}" for j in row) for i, row in enumerate(top)]


def overlap(a: np.ndarray, b: np.ndarray, k: int) -> int:
    """Quanti oggetti hanno in comune i primi k dei due punteggi."""
    return len(set(np.argsort(-a)[:k]) & set(np.argsort(-b)[:k]))


def rank(f: pd.DataFrame, p: dict) -> tuple[pd.DataFrame, dict]:
    """Punteggi dei due metodi, rango combinato (media dei ranghi percentili) e confronto."""
    z = scale(design_matrix(f))
    s_if = isolation_forest(z, p["if_n_estimators"], p["if_max_samples"], p["seed"])
    s_lof = lof(z, p["lof_n_neighbors"])
    r_if, r_lof = percentile_rank(s_if), percentile_rank(s_lof)
    out = f.assign(score_if=s_if, score_lof=s_lof, prank_if=r_if, prank_lof=r_lof,
                   prank_combined=(r_if + r_lof) / 2, drivers=drivers(z))
    # a parità di rango combinato decide Isolation Forest, poi il TIC: ordine deterministico
    out = out.sort_values(["prank_combined", "score_if", "tic"], ascending=[False, False, True])
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    cmp = {"spearman_if_lof": float(spearmanr(s_if, s_lof).statistic),
           **{f"overlap_top{k}": overlap(s_if, s_lof, k) for k in p["compare_top_k"]}}
    return out, cmp
