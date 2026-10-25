# FASE 0 — Rassegna della letteratura

**Tema:** anomaly detection e classificazione automatica nelle curve di luce TESS (2022–2026)
**Stato:** bozza per la scelta della domanda di ricerca. Non contiene codice e non avanza ipotesi di "scoperta".
**Data:** 2026-10-25

Fonti consultate: arXiv (API e full text), NASA ADS e Google Scholar (per riferimenti e citazioni).
Per i lavori marcati con ✱ ho letto il testo completo; per gli altri ho letto l'abstract e le sezioni chiave.

---

## 1. Lavori principali (TESS)

| # | Lavoro | Metodo | Dati (settori / stelle) | Cosa hanno trovato | Limiti dichiarati | Link |
|---|---|---|---|---|---|---|
| 1 | ✱ **Crake & Martínez-Galarza 2023**, MNRAS — *Searching for anomalous light curves in TESS* | Unsupervised Random Forest (URF) su flusso normalizzato + periodogramma; score = 1 − similarità | SPOC PDCSAP 2-min, settori 1–26 (lug 2018 – mag 2020). Ispezione visiva di circa 12.500 curve con score ≥ 0.9 nei settori 13–24 | Circa 43% nane bianche (pulsazioni rapide, incrocio con Gentile Fusillo); classi morfologiche "sinusoidal", "multi-body" (~500), "peaked" (~420), "irregular" (~260), "modulated" (~130), LPV (43); EB profonde a lungo periodo, oscuramenti di YSO; 237 artefatti | URF non distingue artefatti da astrofisica rara. Gli errori di sottrazione del fondo in campi affollati imitano "transiti invertiti" o microlensing. Transiti planetari non rilevati su curve non in fase. Il risultato dipende dalla popolazione di partenza. Analisi per singolo settore. **Settori 22 e 23 esclusi** per artefatti PDC | [arXiv:2301.10264](https://arxiv.org/abs/2301.10264) |
| 2 | **Martínez-Galarza et al. 2021**, MNRAS | URF + UMAP + clustering, con Gaia (colore/luminosità) per gli analoghi | Kepler (metodo base del #1) | Boyajian's star e oggetti simili; famiglie di anomalie | Pensato per Kepler; popolazione diversa da TESS | [arXiv:2009.06760](https://arxiv.org/abs/2009.06760) |
| 3 | ✱ **CLARA — Dasgupta 2025** | URF addestrato su set sintetici, orientato ai transiti; clustering DPMM sugli anomali | SPOC 2-min settori 1–5 (> 87k curve, 384k scoring) | Un cluster DPMM con 16 transiti confermati su 114 candidati (14% contro una baseline dello 0,46%) | Focus sui transiti; solo 5 settori; dipende dal set sintetico | [arXiv:2508.04722](https://arxiv.org/abs/2508.04722) |
| 4 | ✱ **Poznanski 2026** — mappa della variabilità TESS | Quantile graphs / scattering transform → PCA → Self-Organizing Map; strumento web tess-l8.space | Circa 1,5M curve 2-min, tutti i settori disponibili al momento dell'analisi | Mappa stabile tra settori, organizzata per ampiezza, SNR, scala temporale e forma; utile per esplorazione e outlier | "Ogni rappresentazione è distorta a modo suo": dipende da preprocessing e scelte del modello. La compressione 2D piega strutture non convesse, per cui curve simili possono finire in nodi lontani. Le distanze euclidee sulla griglia SOM non sono adatte agli outlier (servono distanze su grafo). **Non è un classificatore né un catalogo di anomalie vagliate** | [arXiv:2605.05324](https://arxiv.org/abs/2605.05324) |
| 5 | **Fetherolf et al. 2023**, ApJS 268, 4 — TESS Stellar Variability Catalog (TESS-SVC) | Periodogramma Lomb-Scargle + criteri di affidabilità | Prime Mission (settori 1–26), 232k stelle 2-min, periodi 0,01–13 d | Circa 46k variabili ad alta confidenza e 38k a confidenza moderata; circa 65k nuove. HLSP [doi:10.17909/f8pz-vj63](https://doi.org/10.17909/f8pz-vj63), VizieR J/ApJS/268/4 | Solo segnali **periodici**; solo Prime Mission; periodi > 13 d esclusi | [arXiv:2208.11721](https://arxiv.org/abs/2208.11721) |
| 6 | **ASTRAFier — Gregory, Audenaert et al. 2026** | Classificatore supervisionato Transformer + BiLSTM + CNN | Training su Kepler/TESS; applicato a circa 2,8M curve QLP dei settori 14, 15 e 26 (campo Kepler) | Accuratezza 94% su Kepler e 88% su TESS; catalogo pubblicato | Supervisionato, quindi vede solo le classi note. Copre solo 3 settori | [arXiv:2604.07437](https://arxiv.org/abs/2604.07437) |
| 7 | **Kliapets et al. 2026** — campo PLATO LOPS2 | Rete neurale profonda + GBDT su curve TGLC | 38M curve, 6M sorgenti (FFI) | Circa 72% delle curve dominate da segnale strumentale; circa 3,6M candidate variabili | La purezza migliora solo filtrando su colore, luminosità e vicini, quindi la contaminazione è il problema dominante | [arXiv:2604.12758](https://arxiv.org/abs/2604.12758) |
| 8 | **Cui, Armstrong & Feng 2023** — Deep-LC | Object detection debolmente supervisionata su curva + spettro di potenza; conformal prediction; modulo OOD | Kepler, TESS, ZTF | Accuratezza 87%; rilevazione out-of-distribution | Le classi sono comunque definite a priori | [arXiv:2311.08080](https://arxiv.org/abs/2311.08080) |
| 9 | **Elizabethson et al. 2023**, AJ 166, 189 | Classificazione morfologica ML di T Tauri | TESS, 3672 candidate T Tauri | 11 classi morfologiche (dippers, bursters, …); 27% in classi miste | Campione pre-selezionato (solo YSO) | [ADS 2023AJ....166..189E](https://ui.adsabs.harvard.edu/abs/2023AJ....166..189E) |
| 10 | **Tardugno Poleo, Eisner & Hogg 2024** — NotPlaNET | CNN per scartare falsi positivi da Planet Hunters TESS | Candidati PHT | Riduzione dei falsi positivi nei transiti | Solo transiti | [arXiv:2405.18278](https://arxiv.org/abs/2405.18278) |
| 11 | **Malik et al. 2022** | Deep learning su etichette citizen-science | TESS | Pianeti a lungo periodo / mono-transiti | Solo transiti | [arXiv:2211.06903](https://arxiv.org/abs/2211.06903) |
| 12 | **Morvan et al. 2022** | Transformer di denoising self-supervised | TESS 2-min | Rappresentazioni e denoising | Non fa anomaly detection diretta | [arXiv:2207.02777](https://arxiv.org/abs/2207.02777) |
| 13 | **Audenaert et al. 2025** | Foundation model causale che separa segnale fisico e strumentale | Kepler + TESS | Rappresentazioni meno contaminate da sistematiche | Fase di ricerca; non è un catalogo | [arXiv:2507.05333](https://arxiv.org/abs/2507.05333) |
| 14 | **Van-Lane et al. 2026** — EncoTESS | Piccolo foundation model per curve 2-min | TESS 2-min | Stima dell'età stellare | Non orientato alle anomalie | [arXiv:2608.25019](https://arxiv.org/abs/2608.25019) |

### Lavori collegati (falsi positivi, casi singoli, ricerche mirate)

- **Bell et al. 2023:** un evento anomalo in HZ 4 nel settore 43 era causato da un **asteroide** in transito nell'apertura. È l'esempio tipico di falso positivo da controllare. [arXiv:2307.15085](https://arxiv.org/abs/2307.15085)
- **Cabrales et al. 2024:** ricerca tecnosegnature (SETI Ellipsoid) nella CVZ, nessuna anomalia trovata. Mostra come gestire un risultato nullo. [arXiv:2402.11037](https://arxiv.org/abs/2402.11037)
- **Dippers da FFI (2022):** ricerca di dippers nelle FFI TESS. [arXiv:2201.09459](https://arxiv.org/abs/2201.09459)
- **Boyajian's star in TESS:** nessun dip profondo nel periodo 2019–2022, mentre uno studio di ricorrenza del 2026 riporta un evento dell'1,1% nel 2019. Mostra quanto siano rari e difficili da confermare gli eventi isolati.
- **RNN-VAE + ensemble di outlier detector su TESS (NHSJS 2026):** lavoro di livello liceale, senza peer review in senso stretto. Lo cito solo come esempio di quanto sia diffuso l'approccio "IF + autoencoder".

### Riferimenti di metodo (non TESS)

- **Gupta, Muthukrishna & Lochner 2024 — Multi-Class Isolation Forest:** i transienti rari vengono isolati condizionando su ciascuna classe nota. Gli autori scrivono che "automating anomaly detection is an open problem". [arXiv:2408.08888](https://arxiv.org/abs/2408.08888)
- **Pruzhinskaya et al. 2026 — Fink/ZTF:** Isolation Forest + Active Anomaly Discovery con feedback di esperti. Ha portato a un AM CVn, una UX Ori, 9 novae nane e 30 nuove SNe. Mostra che **l'interazione con l'esperto conta quanto l'algoritmo**. [arXiv:2603.29511](https://arxiv.org/abs/2603.29511)

---

## 2. Review recenti e domande aperte

### Audenaert 2025 — *Machine learning for stellar variability* (Ap&SS, invited review) ✱
[arXiv:2507.03093](https://arxiv.org/abs/2507.03093) · [doi:10.1007/s10509-025-04460-5](https://doi.org/10.1007/s10509-025-04460-5)

Problemi aperti che la review indica esplicitamente:
1. **Sistematiche non i.i.d.:** i trend strumentali sono correlati a posizione in cielo e sul CCD e al tempo di osservazione. Questo viola l'assunzione i.i.d. e degrada i modelli ML su larga scala. Correggerli in modo robusto è definito "essenziale".
2. **Luce diffusa di Terra e Luna e blending** in campi affollati (pixel TESS da 21″). Sono le contaminazioni dominanti.
3. **Pipeline multiple** (SPOC, QLP, TGLC, …) con correzioni diverse. Confrontarle è suggerito come strategia per separare segnale strumentale e segnale astrofisico.
4. **Troppe classi per il supervisionato:** citizen science e metodi statistici faticano con molte classi. Il suggerimento è classificare in modo grossolano e poi esplorare il dettaglio con l'unsupervised.
5. **Benchmark comuni:** il training set T'DA è proposto come riferimento; mancano benchmark condivisi.
6. **Foundation model multimodali** (Kepler+TESS+spettroscopia, contrastive learning), ancora agli inizi.

### Fotopoulou 2024 — *A review of unsupervised learning in astronomy* (Astronomy & Computing) ✱
[arXiv:2406.17316](https://arxiv.org/abs/2406.17316) · [doi:10.1016/j.ascom.2024.100851](https://doi.org/10.1016/j.ascom.2024.100851)

Punti rilevanti per noi:
- In astronomia **nessun dataset è del tutto sconosciuto**: l'unsupervised va sempre validato contro la conoscenza esistente, cioè i cataloghi. Questo sostiene la nostra FASE 4.
- Lo spazio dei parametri è sparso e ad alta dimensionalità, e incertezze e scatter intrinseco formano un **continuo, non classi discrete**. Il clustering diretto è raramente adatto, mentre riduzione dimensionale e ranking funzionano meglio.
- La comunità è divisa in **silos**: metodi applicati a un solo dataset, senza confronti sistematici. C'è uno spostamento verso self- e semi-supervised.
- **Interpretabilità:** si preferiscono embedding interpretabili (PCA) a quelli opachi quando servono a fare scienza.

---

## 3. Cosa è già stato fatto

- **Mappatura globale delle curve 2-min (Poznanski 2026):** copre tutto il catalogo 2-min fino al momento dell'analisi. Il nostro progetto non può presentarsi come "prima esplorazione unsupervised di TESS".
- **Anomaly detection URF sulla Prime Mission (Crake 2023):** settori 1–26, con ispezione visiva e classi morfologiche. Esiste quindi un **termine di confronto diretto**, ma solo per la Prime Mission.
- **Variabilità periodica (TESS-SVC):** catalogata per la Prime Mission, solo periodi ≤ 13 d.
- **Classificazione supervisionata su larga scala:** ASTRAFier (3 settori, QLP) e Kliapets (LOPS2, TGLC).
- **Transiti:** coperti molto bene (TOI, PHT, NotPlaNET, CLARA, Malik).
- **Classi specifiche:** coperte con metodi dedicati (T Tauri / dippers, EB con IJspeert et al.).

## 4. Cosa NON è stato fatto (o è debole)

1. **Nessun catalogo di anomalie vagliate per la Extended Mission.** Crake si ferma al settore 26 e CLARA al 5. La SOM di Poznanski produce una mappa, non una lista ordinata e vagliata contro SIMBAD/VSX/TOI.
2. **Eventi non periodici.** TESS-SVC e i classificatori basati sul periodogramma sono costruiti per segnali periodici. Crake stesso nota che l'URF non coglie segnali brevi in curve non in fase. Dips singoli, flare isolati, dippers aperiodici e mono-transiti di oggetti non-pianeti restano poco esplorati da un approccio unsupervised generale.
3. **Confronto sistematico tra metodi.** Ogni lavoro usa un solo algoritmo (URF, SOM, IF). Non ho trovato uno studio TESS che confronti, sullo stesso campione, un metodo ad alberi (IF) con uno basato sulla densità (LOF/HDBSCAN) su feature interpretabili, misurandone l'accordo.
4. **Vetting esplicito degli artefatti.** Crake trova 237 artefatti tra i top e Kliapets il 72% di segnali strumentali. Pochi lavori applicano filtri sistematici e riproducibili: contaminazione da vicini Gaia, bordi di settore, momentum dumps, settori problematici, asteroidi, persistenza tra settori.
5. **Riproducibilità.** Nessuno dei lavori pubblica una pipeline completa e ri-eseguibile, dal download fino al cross-match, con run versionati.

---

## 5. Proposte di domanda di ricerca

### Proposta A — Anomalie in un settore recente della Extended Mission, con vetting sistematico

> *"Quali curve 2-min di un singolo settore recente della Extended Mission (es. un settore di Cycle 6–7) risultano anomale secondo due metodi unsupervised indipendenti, e quante di esse sono assenti o classificate diversamente in SIMBAD, VSX e TOI dopo aver rimosso gli artefatti noti?"*

**Pro**
- Lacuna chiara e verificabile: nessun catalogo di anomalie vagliate oltre il settore 26.
- Si allinea alla spec: un settore, alcune migliaia di stelle, due metodi, top 50, cross-match.
- I settori recenti sono, per costruzione, i meno studiati nei cataloghi, quindi la probabilità di trovare oggetti "assenti" è più alta.
- Crake 2023 fa da termine di confronto per la distribuzione delle classi anomale.

**Contro**
- La SOM di Poznanski potrebbe già coprire il settore scelto. Va verificato su tess-l8.space; in quel caso la nostra novità è il vetting, non la mappatura.
- Un settore recente ha meno controparti in letteratura, quindi la classificazione dei candidati sarà più incerta. "Assente dai cataloghi" non significa "nuovo".
- Bisogna scegliere un settore senza problemi noti di scattered light. Da verificare nelle Data Release Notes.

### Proposta B — Eventi isolati e non periodici (dips, flare, dippers aperiodici)

> *"In un settore TESS ricco di stelle giovani o del piano galattico, quali stelle mostrano eventi isolati (dips singoli, flare, oscuramenti aperiodici) che i cataloghi di variabilità periodica non riportano?"*

**Pro**
- Colma una lacuna strutturale: TESS-SVC e i classificatori basati sul periodogramma non vedono questi eventi.
- Le feature richieste dalla spec (dips brevi, eventi isolati) diventano il cuore del progetto anziché un accessorio.
- Gli oggetti di questo tipo (dippers, oscuramenti di YSO, eventi tipo Boyajian) sono scientificamente interessanti per un astronomo.

**Contro**
- È **il caso più esposto ai falsi positivi**: asteroidi (Bell 2023), momentum dumps, bordi di settore, errori del fondo in campi affollati ("transiti invertiti" in Crake 2023), cosmic ray e single-pixel spike. Il vetting della FASE 4 diventa la parte più pesante.
- Un evento singolo in un solo settore è difficile da confermare senza follow-up, quindi molti candidati resteranno "da verificare".
- Nei campi affollati la contaminazione dalle stelle vicine è più alta (pixel da 21″).

### Proposta C — Confronto tra metodi e persistenza tra settori nella CVZ

> *"Per le stelle 2-min della Zona di Visibilità Continua meridionale (osservate in molti settori), quanto concordano Isolation Forest e un metodo a densità (LOF/HDBSCAN) nel ranking delle anomalie, e quante anomalie persistono su più settori indipendenti invece di comparire in uno solo?"*

**Pro**
- La persistenza su più settori è il filtro anti-artefatto più forte disponibile. Crake usa un'idea simile con lo score "high variance".
- Risponde direttamente al problema dei "silos" (Fotopoulou) e alla mancanza di confronti tra metodi.
- Il numero di stelle 2-min della CVZ (alcune migliaia) rientra nella scala della spec.

**Contro**
- La CVZ è il campo **più studiato** di TESS (CVZ di JWST, molte survey), quindi pochi oggetti saranno davvero assenti dai cataloghi.
- Richiede molti settori per stella, quindi il download e la cache sono molto più grandi (circa 13 settori o più per stella, invece di 1).
- Il risultato principale è metodologico (accordo tra metodi), meno "da mostrare" in termini di oggetti nuovi.

### Raccomandazione

**A**, prendendo da C la verifica di persistenza dove esiste un secondo settore per la stessa stella.
- È la domanda con la lacuna più netta e la più fattibile nella scala del progetto.
- Produce una lista di candidati confrontabile con Crake 2023.
- Le feature per eventi isolati (B) restano comunque nel set della FASE 2, e i candidati di quel tipo emergeranno se esistono.

Prima di scaricare dati, nella FASE 1 restano due controlli da fare:
1. Verificare sulle Data Release Notes che il settore scelto non abbia problemi noti.
2. Verificare se è già coperto dalla mappa di Poznanski, e in quel caso dichiararlo nel report.

---

## 6. Cautele che valgono per qualunque scelta

- L'output sarà **una lista di candidati da verificare**, non scoperte.
- "Assente da SIMBAD/VSX/TOI" significa solo "non trovato nei cataloghi interrogati con il raggio di ricerca scelto".
- Ogni candidato riporterà i controlli di falso positivo eseguiti:
  - contaminazione da sorgenti Gaia vicine;
  - posizione rispetto ai bordi di settore e ai momentum dumps;
  - quality flag;
  - passaggio di asteroidi noti, se verificabile.
