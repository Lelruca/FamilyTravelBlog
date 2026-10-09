# Places navigation

`data/place_coordinates.json` stores the reviewed map location for each place
slug. Coordinates were looked up using the Photon API (OpenStreetMap data),
then disambiguated against the destination and chapter text. Each entry keeps
the exact OSM object URL and search query, rather than geocoding on every visit.
https://github.com/komoot/photon/blob/master/docs/api-v1.md

Cities use a central settlement point. Museums, castles and caves use their
own location where available. Regions/islands use a representative point;
the Berkshires entry explicitly records this convention. The Normandy landing
beaches use Juno Beach Centre, which is the site visited in the chapter.

For new places, add a reviewed entry with `lat`, `lon`, `name`, `country_code`,
`source` and `query`. Do not accept the first geocoder result without checking
the country, region and narrative. A place without coordinates remains fully
accessible in the list, and the map reports how many places are located.

Both views generate chapter links from Hugo's `places` taxonomy on individual
chapter pages. No links are inferred from a trip's `geo_countries` field.
The permanent place page lists those same chapters without photographs.

The map uses locally bundled Leaflet 1.9.4 and MarkerCluster 1.5.3 (licenses
under `static/vendor/leaflet/`). Only the basemap tiles require an external
request; they use standard OpenStreetMap tiles with visible attribution.
https://operations.osmfoundation.org/policies/tiles/

After a production build, run `node scripts/verify-places.cjs` to check all
place/chapter relationships and generated chapter URLs against source files.
