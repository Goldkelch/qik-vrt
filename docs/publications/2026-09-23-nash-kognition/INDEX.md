# Warum künstliche Kognition zu oft im Nash-Gleichgewicht stehen bleibt

**Ingolf Lohmann · 23. September 2026**

Kanonische Fassung: [Deutsch](ARTICLE.de.md)

## Menschliche Sprachen

- de: [ARTICLE.de.md](ARTICLE.de.md) — SHA-256 `5ba96c975d385ff6e90b4403cfbc7fa1d6092615c4cf0f79dfcfb8013335fcdc`
- en: [ARTICLE.en.md](ARTICLE.en.md) — SHA-256 `81a55714aef742a327dc743cde30bb575e36d0df2bf6c21fa7637b6266a34c5f`
- fr: [ARTICLE.fr.md](ARTICLE.fr.md) — SHA-256 `ffb18d7907325efae15039dda33ff5ab9b46d25a368c3bd84638a92e0c77696a`
- es: [ARTICLE.es.md](ARTICLE.es.md) — SHA-256 `d1106153cdbd18f0d9a0ab15f0b31e071cb3b1a72e26a8ac6c92a6419a9e7a95`
- pt: [ARTICLE.pt.md](ARTICLE.pt.md) — SHA-256 `712617dccefecb90ccc1cc0d67dbc97bc8c88be3cdf640a2274d8d919997bd9d`
- it: [ARTICLE.it.md](ARTICLE.it.md) — SHA-256 `b9cf5b7b07d25a4fa6623f473b811661824e101087dff06d4cd352569471b42e`
- ru: [ARTICLE.ru.md](ARTICLE.ru.md) — SHA-256 `a62f199696579ca42cef55df30cb673f9aaeae7812dfc2b33790bc281c86b227`
- zh-Hans: [ARTICLE.zh-Hans.md](ARTICLE.zh-Hans.md) — SHA-256 `b10c55bcf9600d991b82ec27ddcb9300ac4de356b1a38607b3258090e909cb01`
- ar: [ARTICLE.ar.md](ARTICLE.ar.md) — SHA-256 `2b3a338079ea3bd9a3491e9d7db78108f24f13f20290ac63c1282a21e06ccc13`
- hi: [ARTICLE.hi.md](ARTICLE.hi.md) — SHA-256 `249e51599c83569ccfc0c280902126f081d5c1cd52f8815b077fde3fce7b7a24`
- ja: [ARTICLE.ja.md](ARTICLE.ja.md) — SHA-256 `af5d26e672e04c222771cb3c69a09ef94d34a07cdb856efb6b589e6ed5e8f7ee`

Die Übersetzungen sind nicht-kanonische, bedeutungserhaltende Fassungen. Bei Abweichungen gilt die deutsche Fassung.

## Maschinenlesbare Semantik

- JSON: [machine/article.json](machine/article.json) — SHA-256 `e0d03e04e1c6eeb3631ef85a5d48c93343f5533892ba88bf7966484c544c28d5`
- YAML: [machine/article.yaml](machine/article.yaml) — SHA-256 `78c8d49f5e4cf01c8f50c53b970f9a224305159ac42da8ef9f5e157bc3036987`
- JSON-LD: [machine/article.jsonld](machine/article.jsonld) — SHA-256 `406505a98489bb434fbae0abd8619f0f6a87236e3866536276ae0bada7d423d6`
- RDF/Turtle: [machine/article.ttl](machine/article.ttl) — SHA-256 `5b9c98869915aff2916adde91d3973524a60f292e0ac907ca0a8810a9566c23b`
- XML: [machine/article.xml](machine/article.xml) — SHA-256 `076c1d12fc4eaf8dc9c6417cd1a78beaf4c4cb4bed71bfe5d8037bc7447d9a15`
- Prolog: [machine/article.pl](machine/article.pl) — SHA-256 `3660db91e5d54082a08a1603209fd0b7f9efa8283ada2ce73845a53b92d644f5`
- TEMDD: [machine/article.temdd](machine/article.temdd) — SHA-256 `ac4895bd4e25e82370ebbb34c2958ab7dbf6e528af02920f158cb13b1d9e4e33`

Diese Repräsentationen sind keine Behauptung, natürliche Sprache lasse sich verlustfrei in Programmiersyntax übersetzen. Sie materialisieren die zentralen formalen Aussagen, Evidenzgrenzen und Laufzeitsemantik für Maschinen.

## Kerninvarianten

[
LOCAL\_STABILITY\neq GLOBAL\_CORRECTNESS
]

[
LOCAL\_EFFECT\_ACK\_DONE\neq UNIVERSAL\_EFFECT\_ACK\_DONE
]

[
UNCHANGED\neq DONE
]

[
STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE
\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS
]

[
DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS
\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION
]

## Zenodo

Status: **PENDING_EXACT_OWNER_AUTHORIZATION**.

Diese Repository-Materialisierung ist noch keine Zenodo-Veröffentlichung. Der vorhandene fail-closed QIK-VRT-Publisher verlangt eine exakte, kandidatenspezifische Owner-Autorisierung sowie die bestehenden Machine-Proof-/Prepublication-Return-Gates. Eine DOI wird erst nach tatsächlicher Veröffentlichung und frischem öffentlichen Readback eingetragen.
