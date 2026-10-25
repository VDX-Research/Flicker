"""I target SPOC di un settore, con la magnitudine TESS dal TIC."""
import pandas as pd
from astroquery.mast import Catalogs, Observations


def sector_targets(sector: int, cadence_s: int = 120) -> pd.DataFrame:
    """Una riga per curva di luce SPOC del settore alla cadenza data: tic, obs_id, ra, dec."""
    r = Observations.query_criteria(obs_collection="TESS", provenance_name="SPOC",
                                    dataproduct_type="timeseries", sequence_number=sector)
    df = r["target_name", "obs_id", "s_ra", "s_dec", "t_exptime"].to_pandas()
    df = df[df.t_exptime == cadence_s].drop(columns="t_exptime")
    df = df.rename(columns={"target_name": "tic", "s_ra": "ra", "s_dec": "dec"})
    df["tic"] = df.tic.astype("int64")
    return df.sort_values("tic").drop_duplicates("tic").reset_index(drop=True)


def tic_magnitudes(tics: list[int], chunk: int = 1000) -> pd.DataFrame:
    """Tmag e contratio dal TIC (MAST), per blocchi."""
    out = []
    for i in range(0, len(tics), chunk):
        r = Catalogs.query_criteria(catalog="Tic", ID=[str(t) for t in tics[i:i + chunk]])
        out.append(r["ID", "Tmag", "contratio"].to_pandas())
    df = pd.concat(out, ignore_index=True).rename(columns={"ID": "tic", "Tmag": "tmag"})
    df["tic"] = df.tic.astype("int64")
    return df.drop_duplicates("tic")
