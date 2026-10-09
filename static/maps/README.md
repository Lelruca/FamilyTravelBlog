# Travel atlas geometry

The country outlines embedded in `layouts/partials/travel-world-map.html` come
from Natural Earth, 1:110m admin 0 countries (public domain):
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson

The atlas uses an equirectangular projection. Its schematic Europe–Asia divide
follows the Urals, Ural River, Caspian Sea, Greater Caucasus and Turkish straits.
Clipping separates continent hit areas within Russia, Kazakhstan, Turkey,
Georgia and Azerbaijan without changing the country outlines.

The flags in `static/flags/` are from the MIT-licensed flag-icons project:
https://github.com/lipis/flag-icons/tree/main/flags/4x3
The license is retained in `static/flags/LICENSE`.

Trip counts, availability, cover images and links are generated from Hugo's
country sections and `geo_countries`, rather than hard-coded in the map.
