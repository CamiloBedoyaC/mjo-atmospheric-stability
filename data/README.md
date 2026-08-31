# Fuentes y trazabilidad de los datos

Los datos crudos no se distribuyen en este repositorio. El proyecto utiliza
fuentes meteorológicas oficiales y conserva sus identificadores, periodos y
hashes para documentar la procedencia de los resultados.

## 1. Radiosondeos IGRA

Fuente: NOAA/NCEI — Integrated Global Radiosonde Archive, IGRA 2.

- Página del producto:
  https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive

- Estación PSM00091408 — Koror, Palau:
  https://www.ncei.noaa.gov/pub/data/igra/data/data-por/PSM00091408-data.txt.zip

- Estación FMM00091334 — Truk/Chuuk, Micronesia:
  https://www.ncei.noaa.gov/pub/data/igra/data/data-por/FMM00091334-data.txt.zip

- Lista oficial de estaciones:
  https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/doc/igra2-station-list.txt

- Descripción del formato:
  https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/doc/igra2-data-format.txt

El snapshot utilizado en los resultados publicados contiene radiosondeos hasta
el 5 de septiembre de 2025.

## 2. Índice RMM de la MJO

Fuente: Australian Bureau of Meteorology.

- Monitor de la MJO:
  https://www.bom.gov.au/climate/mjo/

- Archivo RMM:
  https://www.bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt

El archivo utilizado en los resultados publicados termina el 24 de febrero de
2024. Por esta razón, los radiosondeos posteriores conservan sus indicadores de
estabilidad, pero no participan en los composites por fase MJO.

## 3. Archivos derivados incluidos

- `station_selection.csv`: selección auditada de las dos estaciones.
- `input_manifest.sha256`: huellas digitales de los insumos del snapshot.
- `outputs/daily_2stations.csv`: serie diaria procesada.
- `outputs/daily_2stations.parquet`: copia equivalente en formato Parquet.

## Reproducción

Sin un snapshot archivado, los archivos descargados desde las fuentes oficiales
pueden incorporar actualizaciones. El flujo seguirá siendo reproducible, pero
los resultados pueden variar ligeramente respecto a la publicación original.