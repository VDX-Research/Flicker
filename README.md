# vdx-research-tess

Pipeline riproducibile di VDX Research che cerca, nelle curve di luce TESS del settore 103,
oggetti dal comportamento anomalo non ancora presenti nei cataloghi. Il risultato è una lista di
**candidati da verificare**, non di scoperte.

## Dati

| | |
|---|---|
| Settore | 103 (anno 8) |
| Prodotto | curve di luce SPOC a 2 minuti (`*_lc.fits`), flusso PDCSAP |
| Data release | DR141 (`DATA_REL = 141`, release note DRN141) |
| Versione SPOC | `spoc-5.0.126-20251212` |
| Data dei file (header `DATE`) | 2026-06-10 |
| Scarico | campione di sviluppo: 2026-10-25 (23:13–23:19 UTC), da `archive.stsci.edu/missions/tess/tid/s0103/`; corsa finale: data in `data/products_s103_all.json` |
| Target | 13.000 curve a 120 s (più 2.566 a 20 s, non usate) |

Le versioni sono lette dall'header di ogni file scaricato e salvate in
`data/products_s103_<sample|all>.json`; il manifest `data/manifest_s103_<...>.csv` registra per
ogni curva dimensione, sha256, data di scarico, `DATA_REL` e `PROCVER`. Lo scarico rifiuta
file con una data release diversa da quella di `config/pipeline.toml`.

### Persistenza su altri settori

Il controllo di persistenza usa solo curve SPOC (2 min e 20 s) di settori con note di rilascio
pubblicate, cioè fino al settore 104 (`scripts/sector_overlap.py`, risultato in
`data/overlap_s103.csv`). Dei 13.000 TIC del settore 103:

| altri settori SPOC (≤ 104) | TIC | % |
|---|---|---|
| anno 8, settori 99–104 | 9.550 | 73,5 |
| anno 7, settori 91–97 | 3.687 | 28,4 |
| anni 1–5, settori 1–69 | 6.583 | 50,6 |
| almeno uno | 11.033 | 84,9 |
| nessuno | 1.967 | 15,1 |

I settori 105–107 hanno già curve su MAST ma non ancora le note di rilascio: sono esclusi da
questa versione perché ogni dato usato deve essere citabile. Potranno servire in una seconda
versione. I candidati senza altro settore sono etichettati "persistenza non verificabile",
restano nella lista e hanno una sezione a parte nel report.

## Protocollo: campione di sviluppo, poi parametri congelati

1. Tutte le soglie e i parametri (`config/pipeline.toml`) si decidono **solo** su un campione di
   sviluppo di 3.000 target, estratto in modo riproducibile: seed 103, stratificato per
   magnitudine TESS (classi `tmag_edges`, allocazione proporzionale con il metodo dei resti
   maggiori). Il campione è in `data/sample_s103.csv`.
2. A pipeline stabile si imposta `frozen = true` e si esegue **una sola** corsa finale su tutti i
   13.000 target senza più cambiare nulla. Lo script rifiuta `--all` se i parametri non sono
   congelati, e ogni esecuzione registra l'impronta (sha256) dei parametri usati.

## Pulizia (FASE 1)

Per ogni curva, in ordine, con il numero di cadenze tolte da ogni passo nel riepilogo
`data/clean_s103_<...>.csv`:

1. **Flag di qualità**: scartate le cadenze con un bit della maschera 16575 in `QUALITY`, cioè il
   default di lightkurve 2.6 (17087) meno "Impulsive outlier" (512). Un outlier impulsivo può
   essere un evento breve reale: resta, e lo valuta la fase di scarto degli artefatti.
2. **Valori non finiti** in tempo, flusso o errore (tra cui le cadenze con luce diffusa, che SPOC
   mette già a NaN nel PDCSAP).
3. **Buchi**: un buco di più di 0,5 giorni separa due segmenti; i frammenti più brevi di 0,5
   giorni sono scartati.
4. **Normalizzazione**: ogni segmento è diviso per la propria mediana.
5. Curve con meno di 1.000 cadenze valide escluse, e curve con mediana del flusso ≤ 0 in un
   segmento (fondo sovrasottratto: non normalizzabili).

Sul campione di sviluppo (3.000 curve, 18.969 cadenze l'una, 3 segmenti): il flag di qualità
toglie in media 2.144 cadenze (11,3%), i valori non finiti 1.626 (8,6%), i frammenti corti 0;
restano in media 15.199 cadenze. Escluse 20 curve, tutte per mediana ≤ 0, tutte stelle deboli
(Tmag 13,6–20,6, mediana 18,6). Ne restano 2.980.

Nota sul campione: il 34% dei target del settore (4.400) ha Tmag ≥ 16 (stelle da Gaia DR2, fino a
Tmag 20,8). Stanno nell'unica classe Tmag ≥ 13, dove l'estrazione è casuale, quindi la loro
proporzione nel campione è rappresentativa; le soglie della FASE 2 ne terranno conto.

Niente detrending e niente sigma-clipping: toglierebbero i segnali anomali che cerchiamo.
Centroidi, fondo e `QUALITY` restano nella curva pulita per lo scarto degli artefatti.

## Uso

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[test]"
.venv/bin/python -m pytest

.venv/bin/python scripts/sector_overlap.py    # persistenza: altri settori per TIC
.venv/bin/python scripts/fase1.py --sample    # campione di sviluppo
.venv/bin/python scripts/fase1.py --all       # corsa finale, solo con frozen = true
```

Le curve scaricate (`data/cache/lc/`, ~1,9 MB l'una, ~25 GB in tutto) e quelle pulite
(`data/cache/clean/`, parquet) sono in cache locale e non nel repository.

## VDX Core

I risultati vanno nel modulo Research di VDX Core tramite `vdx-core-client`. Con le variabili
`VDX_CORE_URL` e `VDX_TOKEN` (token di sorgente del progetto, da
`scripts/create-research-source.ts` in Core) i messaggi sono inviati; senza, sono scritti in
`data/outbox/` e possono essere inviati più tardi: l'invio è idempotente (oggetti per id esterno,
esecuzioni per chiave).

Nota per macOS: se il repository sta in una cartella sincronizzata con iCloud (Desktop) il file
`.pth` dell'installazione editable riceve il flag `hidden` e Python 3.12 lo ignora. Per questo
gli script e pytest aggiungono `src/` al percorso da soli.

## Fasi

- FASE 0: rassegna della letteratura, `docs/literature.md`
- FASE 1: dati, pulizia, cache, Dataset in Core
