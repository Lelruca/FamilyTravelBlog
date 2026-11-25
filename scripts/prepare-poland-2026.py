"""«Наша Польша» (November 2026): owner's photo selection on Drive -> verified archive -> R2 copies -> pages.

Continues Codex's draft of 24 Nov 2026 (his inventory, captions and paragraph assignment), with the layout
reworked to DESIGN_PHOTOS.md and the owner's layout rules (no lone vertical photo, a row of three holds at most
one horizontal one, key family shots and masterpieces large), two photos he had left out (Wroclaw day 1, 15:13
and 15:15) placed, and Olga's photo on the Oder embankment kept (it is a different shot, not a duplicate).

The owner put her selected full originals into five chapter folders of the archive and wrote the five chapter
texts plus two caption files (Drive: Family Travel Blog Photos/Отчеты). Photo numbers below are the positions
in Codex's inventory (.tmp/poland-2026/inventory-codex.json): files of a chapter folder sorted by capture time.
After the archive stage the manifest (media-manifests/poland-2026.json, also on Drive) holds everything; the
later stages read only the manifest and the archive.

Stages (python -I scripts/prepare-poland-2026.py <stage>):
  check      compare the Drive folders with the inventory and the layout (changes nothing)
  archive    rename the originals to NN_<name> in page order (unused: zz_не использовано_<name>), copy the
             source texts into the trip folder, write both manifests
  -- then: node scripts/check-drive-sync.cjs "Europe/2026 - Польша" --write
  display    screen copies (2000 px long side, EXIF rotation, no upscaling, no EXIF/GPS) and H.264 copies of the
             HEVC videos into static/r2/poland-2026/<chapter>/, sizes and captions into data/photos/poland-2026.json
  captions   photo captions from the owner's Facebook posts (FB_CAPTIONS) into the manifest and data/photos
  -- then: node scripts/upload-to-r2.cjs poland-2026
  verify-r2  fetch every public R2 URL and compare its bytes (SHA-256) with the local copy
  render     write the trip and chapter pages
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, html, json, re, shutil, subprocess, sys, urllib.request

ROOT = Path(__file__).resolve().parents[1]
DRIVE = Path('G:/My Drive/Family Travel Blog Photos')
ARCHIVE = DRIVE / 'Europe/2026 - Польша'
SOURCES = DRIVE / 'Отчеты'
INVENTORY = ROOT / '.tmp/poland-2026/inventory-codex.json'
MANIFEST = ROOT / 'media-manifests/poland-2026.json'
TRIP = ROOT / 'content/europe/poland/poland-2026'
SLUG = 'poland-2026'
BASE = 'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'
LONG_SIDE = 2000

# Layout: after paragraph N (1-based, non-empty lines of the chapter text) the blocks in order.
#   ('r', [..]) row · ('x', [..]) row with museum-style labels under captioned photos · ('m', [..]) mosaic,
#   first photo the main one · ('v', n) video · ('b', n) photo beside that (short) paragraph.
# A photo is its number in the chapter folder, or (chapter, number) for one that the owner put into another
# chapter's folder; the archive stage moves it into the folder of the chapter that shows it.
CHAPTERS = [
 dict(slug='wroclaw-1', folder='01 - Вроцлав - 1', title='Вроцлав - первое впечатление', source_title='Вроцлав - 1', source='Вроцлав - 1.md', date='2026-11-14',
  city='Вроцлав', places=['wroclaw'], hero=42, layout={
   1: [('r', [1])],
   3: [('r', [2, 3])],
   4: [('m', [4, 5, 6])],
   6: [('r', [21, 32, 22]), ('r', [27, 23, 24]), ('r', [28]), ('r', [29, 30, 25]), ('r', [26, 31])],
   7: [('r', [7, 11, 8]), ('r', [15]), ('r', [13, 14, 72]), ('r', [9, 10, 16]), ('r', [17, 18]), ('r', [19, 20])],
   8: [('r', [34, 35]), ('r', [33, 36]), ('r', [37, 38]), ('r', [39]), ('r', [40, 74, 41]), ('r', [43])],
   9: [('r', [44, 47, 46]), ('r', [45, 48]), ('r', [50, 54, 55]), ('r', [53, 52, 51]), ('v', 49), ('r', [57, 56, 58]), ('v', 59)],
   10: [('r', [60, 62, 65]), ('r', [68, 71])],
   11: [('r', [66, 69, 70])],
   14: [('r', [64, 67])],
   15: [('r', [61, 63])],
   16: [('r', [12])]},
  unused={73: 'WhatsApp copy of photo 58 (the lamplighter): same frame, smaller'}),
 dict(slug='wroclaw-2', folder='02 - Вроцлав - 2', title='Вроцлав - панорама и гномики', source_title='Вроцлав - 2', source='Вроцлав - 2.md', date='2026-11-15',
  city='Вроцлав', places=['wroclaw'], hero=36, layout={
   2: [('r', [13, 14])],
   3: [('r', [26, 15]), ('r', [16, 17]), ('r', [18, 22, 23]), ('r', [19, 21]), ('r', [24, 25])],
   4: [('r', [20]), ('r', [27, 28]), ('r', [29, 30])],
   5: [('r', [12, 31]), ('v', 32)],
   6: [('r', [40, 1, 8]), ('r', [34, 35])],
   7: [('r', [39, 38]), ('r', [37])],
   8: [('b', 42)],
   9: [('r', [2, 3, 5]), ('r', [6, 9, 10]), ('r', [11, 33, 41]), ('r', [43, 44, 45]), ('r', [46, 47, 49]),
       ('r', [48, 54]), ('r', [51, 50]), ('r', [52, 53])],
   10: [('r', [55, 56]), ('r', [57, 58])],
   11: [('r', [59, 60])]},
  unused={4: 'Same file as Wroclaw 1 photo 40 (shown there, day 1)', 7: 'Same file as Wroclaw 1 photo 58 (shown there, day 1)',
          61: 'Same file as Wroclaw 1 photo 74 (shown there, day 1)'}),
 dict(slug='krakow-1', folder='03 - Краков - 1', title='Краков - Рыночная площадь и костёлы', source_title='Краков - 1', source='Краков - 1.md', date='2026-11-16',
  city='Краков', places=['krakow'], hero=52, layout={
   1: [('r', [50, 37])],
   2: [('r', [19, 20]), ('r', [21, 5]), ('x', [25, 32, 38])],
   3: [('r', [22, 23, 24])],
   4: [('r', [2, 3]), ('r', [1, 4]), ('x', [18, 33]), ('r', [53])],
   6: [('r', [51, 31]), ('r', [27, 26]), ('r', [28, 29, 30])],
   7: [('x', [43, 46, 45]), ('r', [44, 49]), ('r', [47, 48])],
   8: [('r', [40, 41, 42])],
   9: [('x', [10, 6, 9]), ('r', [12, 14]), ('r', [13, 16]), ('r', [11, 15, 17])],
   10: [('r', [8, 7])],
   11: [('x', [34]), ('r', [35, 36])]},
  unused={}),
 dict(slug='krakow-2', folder='04 - Краков - 2', title='Краков - музеи и Вавель', source_title='Краков - 2', source='Краков - 2.md', date='2026-11-17',
  city='Краков', places=['krakow'], hero=32, layout={
   2: [('r', [1, 26]), ('x', [5, 2, 7]), ('r', [11, 13, 9]), ('r', [18, 15]), ('r', [12, 14, 16])],
   3: [('r', [4, 21, 23]), ('x', [19, 24]), ('r', [22, 25])],
   4: [('r', [92]), ('x', [87]), ('r', [89, 86]), ('r', [91])],
   5: [('r', [27, 28]), ('r', [('krakow-1', 39), 29]), ('r', [33, 34]), ('r', [31, 30]), ('r', [35, 36, 38])],
   6: [('r', [54, 55]), ('x', [58]), ('x', [56, 60]), ('r', [61, 62]), ('r', [63, 64]), ('x', [72, 73, 76]),
       ('r', [74, 75, 79]), ('r', [78, 80, 81]), ('m', [84, 82, 83])],
   7: [('r', [37])],
   8: [('r', [40, 39]), ('r', [41]), ('r', [42, 43]), ('r', [44, 48]), ('r', [49]), ('r', [45, 46, 47]),
       ('r', [51, 50]), ('r', [52, 93, 53])],
   9: [('r', [65, 66]), ('r', [67, 68]), ('r', [69, 70])]},
  unused={i: 'Museum label or information screen: source of a caption, not a photo of the story'
          for i in [3, 6, 8, 10, 17, 20, 57, 59, 71, 77, 85, 88, 90]}),
 dict(slug='krakow-3', folder='05 - Краков - 3', title='Соляные шахты Велички', source_title='Краков - 3', source='Краков - 3.md', date='2026-11-18',
  city='Краков, Величка', places=['krakow', 'wieliczka'], hero=14, layout={
   1: [('r', [27, 2])],
   3: [('r', [3, 4, 8])],
   4: [('r', [5, 6, 9])],
   5: [('r', [10, 11, 12]), ('r', [13, 15, 16]), ('r', [17, 18]), ('r', [19, 20, 21]), ('r', [22, 23, 25]), ('r', [24, 26])],
   7: [('r', [28, 29])],
   8: [('r', [1, 31, 32]), ('r', [30, 33]), ('r', [34, 35])],
   9: [('r', [36, 38])],
   10: [('r', [37])],
   12: [('r', [39])]},
  unused={7: 'Near-duplicate of photo 6: the same salt sculpture of Kinga in the same second, from the second phone'}),
]
# The owner's choice on 24 Nov 2026 (first a Kraków city view, which cut the church): Tumski island over the Oder
TRIP_COVER = dict(chapter='wroclaw-1', photo=39, position='center 60%')
DRAFT = 'false'  # published with the owner's «Публикуем», 24 Nov 2026
# Sights named in each chapter text or in the owner's photo captions (data/attractions.json)
ATTRACTIONS = {
 'wroclaw-1': ['wroclaw--rynochnaya-ploshchad', 'wroclaw--ratusha', 'wroclaw--muzey-vroclavskogo-universiteta', 'wroclaw--oratorium-marianum',
               'wroclaw--tumskiy-ostrov', 'wroclaw--kafedralnyy-sobor'],
 'wroclaw-2': ['wroclaw--natsionalnyy-muzey', 'wroclaw--ratslavitskaya-panorama', 'wroclaw--sobor-marii-magdaliny', 'wroclaw--most-pokayannits',
               'wroclaw--gnomiki'],
 'krakow-1': ['krakow--gorodskaya-stena', 'krakow--rynochnaya-ploshchad', 'krakow--sukonnye-ryady', 'krakow--mariatskiy-kostel', 'krakow--bazilika-svyatogo-frantsiska',
              'krakow--pavilon-vyspyanskogo', 'krakow--collegium-maius', 'krakow--kostel-svyatoy-anny', 'krakow--eros-svyazannyy'],
 'krakow-2': ['krakow--muzey-chartoryyskikh', 'krakow--galereya-v-sukennitsakh', 'krakow--vavelskiy-zamok', 'krakow--vavelskiy-sobor'],
 'krakow-3': ['wieliczka--solyanaya-shakhta', 'wieliczka--chasovnya-svyatoy-kingi', 'krakow--krakovskaya-opera'],
}

# Captions: the owner's photo captions on her five Facebook posts about Poland (personal profile, read in Chrome
# on 24 Nov 2026), verbatim, emoji included. They supersede the earlier caption files (archived in «Источники»):
# same texts, a few later edits by her. Photos were matched to the originals by a 6x6 fingerprint of the Facebook
# copy (.tmp/poland-2026/fb-captions.json); two captions name the same place shown on another frame here.
# Not used: «Вот до Церкви технологии дошли!!!» (donation terminal) and «Асаф…» (organ figure) — those two
# photos are not in her Drive selection.
FB_POSTS = {'wroclaw-1': 'pcb.40742818735302302', 'wroclaw-2': 'pcb.40767182536199255', 'krakow-1': 'pcb.40986548600929313',
            'krakow-2': 'pcb.40988195647431275', 'krakow-3': 'pcb.40988373230746850'}
FB_CAPTIONS = [  # (Facebook photo id, chapter, original file name, caption[, note])
 ('40742758985308277', 'wroclaw-1', '20261114_144923.jpg', 'Здание университета'),
 ('40742763041974538', 'wroclaw-1', '20261114_145212.jpg', 'Бесконечная очередь'),
 ('40742764881974354', 'wroclaw-1', '20261114_145236.jpg', 'Минерва, богиня мудрости. Её легко узнать: шлем, рядом сова, а на щите голова Медузы Горгоны. Для университета самая подходящая хозяйка 🙂'),
 ('40742766348640874', 'wroclaw-1', '20261114_145532.jpg', 'Герб Габсбургов: двуглавый орёл, а вокруг гербы их земель (Арагон, Сицилия, Иерусалим, Бургундия, Милан, Моравия, Тироль...). Университет основал в 1702 году император Леопольд I, поэтому Габсбурги здесь повсюду.'),
 ('40742768071974035', 'wroclaw-1', '20261114_150010.jpg', 'Императорская лестница. Говорят, самая парадная лестница во Вроцлаве. На её сводах аллегории всех силезских княжеств'),
 ('40742769911973851', 'wroclaw-1', '20261114_150101.jpg', 'Ораториум Марианум. Барочный зал, построен в 1728–1741 годах как часовня, с 1810 года это музыкальный зал университета.', 'another frame of the same hall on Facebook'),
 ('40742778751972967', 'wroclaw-1', '20261114_151224.jpg', 'Город на 12 островах основан'),
 ('40742780835306092', 'wroclaw-1', '20261114_151355.jpg', 'Вокзал и очень современные узкие трамваи'),
 ('40742802458637263', 'wroclaw-1', '20261114_154738.jpg', 'Это колонна Христа Царя Вселенной. Подпись:\nХристос Царь Вселенной. Колонну поставили за Кафедральным собором в 2000 году, к тысячелетию Вроцлавской епархии.'),
 ('40742805788636930', 'wroclaw-1', '20261114_163313.jpg', 'Очень прикольно ходить и читать вывески'),
 ('40743070085277167', 'wroclaw-1', '20261114_162959.jpg', 'Разруха - в головах!'),
 ('40742734841977358', 'wroclaw-1', '20261114_135901.jpg', 'Ну прямо наши пятиэтажки вдоль дороги!'),
 ('40742746468642862', 'wroclaw-1', '20261114_143528.jpg', 'Ратуша на Рыночной площади. Готика, строили её почти 250 лет, с конца 13 до середины 16 века. Считается старейшей сохранившейся ратушей в Польше.', 'another frame of the same building on Facebook'),
 ('40742750498642459', 'wroclaw-2', '20261114_143845.jpg', 'Собор Святой Марии Магдалины.'),
 ('40742755488641960', 'wroclaw-1', '20261114_144701.jpg', 'Университетский дворик'),
 ('40767126812871494', 'wroclaw-2', '20261115_111722.jpg', 'Саркофаг князя Генриха IV Праведного, 1290 год. Камень, до сих пор видны остатки раскраски и позолоты.'),
 ('40767131336204375', 'wroclaw-2', '20261115_112442.jpg', 'Бог Отец с Адамом и Евой в раю, 1537 год. Надгробная картина-эпитафия из костёла Святой Елизаветы, художник местный, вроцлавский.'),
 ('40767132776204231', 'wroclaw-2', '20261115_112812.jpg', 'Вот у меня первое впечатление было от этого зала - "шкатулка палех". Как интересно работает наш мозг.'),
 ('40767135746203934', 'wroclaw-2', '20261115_113628.jpg', 'Святая Ядвига, 1704–1705 годы. Скульптор Томас Вайсфельд, из костёла Святого Креста.'),
 ('40767137159537126', 'wroclaw-2', '20261115_113654.jpg', 'Святой Варфоломей, 1704–1705 годы. Скульптор Томас Вайсфельд, из костёла Святого Креста.'),
 ('40767139492870226', 'wroclaw-2', '20261115_114742.jpg', 'Замки тоже произведения искусства!'),
 ('40767140659536776', 'wroclaw-2', '20261115_115637.jpg', 'Мечник и Вацлав, 1857 год. Художник Леон Каплиньский, сцена из поэмы Мальчевского «Мария»: отец героини и её муж.'),
 ('40767141959536646', 'wroclaw-2', '20261115_120925.jpg', 'Хеленка, 1900 год. Станислав Выспянский написал свою маленькую дочь.'),
 ('40767143062869869', 'wroclaw-2', '20261115_121029.jpg', 'Валигура, войт из Воли Юстовской, 1874 год. Художник Анджей Грабовский. Войт — это деревенский староста,'),
 ('40986239060960267', 'krakow-1', '20261116_154535.jpg', '"Француз под Москвой"'),
 ('40986239780960195', 'krakow-1', '20261117_093923.jpg', 'С такой командой позитива не получишь'),
 ('40986239704293536', 'krakow-1', '20261118_140406.jpg', 'Мариацкий костёл'),
 ('40986354507615389', 'krakow-1', '20261117_122844.jpg', 'Старинная нумерация - "под белочкой"'),
 ('40986354610948712', 'krakow-1', '20261117_124508.jpg', 'Дом в 3 окна был стандартом. За 4-е надо было сильно даплачивать налоги и поэтому некоторые потом вынуждены были 4-е окно заделывать'),
 ('40986355050948668', 'krakow-1', '20261117_125823.jpg', 'Нож в Суконных рядах — символ Магдебургского права, которое Краков получил в 1257 году. Город обрёл самоуправление и собственный суд, с правом судить и наказывать преступников.'),
 ('40986448700939303', 'krakow-1', '20261118_133241.jpg', 'Францисканский храм — росписи Станислава Выспянского.'),
 ('40986448660939307', 'krakow-1', '20261118_133341.jpg', 'Францисканский храм — росписи Станислава Выспянского.'),
 ('40986448427605997', 'krakow-1', '20261118_133547.jpg', 'Францисканский храм — росписи Станислава Выспянского.'),
 ('40986448550939318', 'krakow-1', 'PXL_20261118_123413316.jpg', 'Францисканский храм — росписи Станислава Выспянского.'),
 ('40986448647605975', 'krakow-1', 'PXL_20261118_123606904.jpg', 'Францисканский храм — росписи Станислава Выспянского.'),
 ('40986461344271372', 'krakow-1', '20261116_112130.jpg', 'Collegium Maius — старейшее здание Ягеллонского университета.'),
 ('40986463754271131', 'krakow-1', '20261116_111555.jpg', 'Университетский храм Святой Анны'),
 ('40986471744270332', 'krakow-1', '20261117_130831.jpg', '«Eros Bendato» («Связанный Эрос») — скульптура Игоря Миторая.'),
 ('40986472050936968', 'krakow-1', '20261117_135529.jpg', 'Тушить факелы'),
 ('40986472040936969', 'krakow-2', '20261117_142537.jpg', 'Висла'),
 ('40986472117603628', 'krakow-1', '20261118_132449.jpg', 'Pawilon Wyspiańskiego,'),
 ('40986472210936952', 'krakow-1', '20261118_132509.jpg', 'Pawilon Wyspiańskiego,'),
 ('40986472790936894', 'krakow-1', '20261118_132554.jpg', 'Pawilon Wyspiańskiego,'),
 ('40988044400779733', 'krakow-2', '20261117_143414.jpg', 'Вавель'),
 ('40987775870806586', 'krakow-2', '20261117_101400.jpg', 'Музей Чарторыйских'),
 ('40987773037473536', 'krakow-2', '20261117_102245.jpg', 'Портрет княгини Изабелы Чарторыйской, 1796 год.'),
 ('40987772954140211', 'krakow-2', '20261117_101833.jpg', 'Портрет князя Константина Чарторыйского, 1821 год.'),
 ('40987772927473547', 'krakow-2', '20261117_102821.jpg', 'Портрет Лукаша Опалинского, 1635–1640 годы.'),
 ('40987772827473557', 'krakow-2', '20261117_102914.jpg', 'Маршальские жезлы - очень меня впечатлили!'),
 ('40987772967473543', 'krakow-2', '20261117_103147.jpg', 'Шатер, захваченый у турков - победа над ними очень великое дело поляков!'),
 ('40987879140796259', 'krakow-2', '20261117_105044.jpg', 'Микеле ди Якопо Тозини. «Венера-победительница». Около 1565–1575 годов - первоначально висела в паре с Леонардо'),
 ('40987946184122888', 'krakow-2', '20261118_150124.jpg', 'Галерея польского искусства XIX века в Суконных рядах (Sukiennice)'),
 ('40987946410789532', 'krakow-2', '20261118_141453.jpg', 'Январий Суходольский. «Отступление из-под Москвы. Эпизод 1812 года», 1854'),
 ('40988044334113073', 'krakow-2', '20261117_140513.jpg', 'Вавель'),
 ('40988044434113063', 'krakow-2', '20261117_143638.jpg', 'Собор с часовнями'),
 ('40988044034113103', 'krakow-2', '20261117_153412.jpg', 'Очень мне освящение понравилось, оно конечно электрическое, но в виде свечей и прямо "темно" там в залах!'),
 ('40988075574109949', 'krakow-2', '45b7e0dd-c6e7-4539-98c2-ebefe1ca454c.jpg', 'Серега с Gemini'),
 ('40988130127437827', 'krakow-2', 'PXL_20261118_103754979.jpg', 'Собор Святых Станислава и Вацлава'),
 ('40988130234104483', 'krakow-2', 'PXL_20261118_103922629.jpg', 'Символическое надгробие Владислава III Варненчика — сына Ягайло, короля Польши и Венгрии. В 1444 году он погиб в битве с турками под Варной, в возрасте 20 лет. Его тело так и не нашли.'),
 ('40988132637437576', 'krakow-2', 'PXL_20261118_103953867.jpg', 'Надгробие Владислава II Ягайло — короля Польши и основателя династии Ягеллонов. В 1410 году он возглавил польско-литовское войско, разгромившее Тевтонский орден в Грюнвальдской битве.'),
 ('40988132337437606', 'krakow-2', 'PXL_20261118_104625843.jpg', 'Наверх!'),
 ('40988132687437571', 'krakow-2', 'PXL_20261118_105738408.jpg', 'Это надгробный памятник королю Яну III Собескому и его жене Марии Казимире, созданный в 1753–1760 годах. Вверху — их портреты в медальонах, на рельефе — битва под Веной, внизу — турецкие пленники. Так увековечили военную славу короля.'),
 ('40988132994104207', 'krakow-2', 'PXL_20261118_110449472.jpg', 'Надгробие Казимира IV Ягеллончика — сына Ягайло, короля Польши и великого князя литовского. Победив Тевтонский орден в Тринадцатилетней войне, он вернул Польше выход к морю. Мраморное надгробие создали Вит Ствош и Йорг Хубер около 1492 года.'),
 ('40988132824104224', 'krakow-2', 'PXL_20261118_111005120.jpg', 'Тадеуш Костюшко'),
]
CAPTION_FILES = ['Краков - 1 - подписи.md', 'Краков - 2 - подписи.md']  # earlier source, kept in the archive
CAPTION_FIXES = [('даплачивать', 'доплачивать'), ('захваченый', 'захваченный'), ('освящение понравилось', 'освещение понравилось')]  # obvious typos only, display
VIDEO_POSTERS = {'wroclaw-1/PXL_20261114_144817606.mp4': 2.0}  # first frame blurred; the lamplighter at 2 s
VIDEO_RECIPE = ['-map', '0:v:0', '-map', '0:a:0', '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', '-map_metadata', '-1']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def site_name(n): return re.sub(r'\((\d+)\)', r'-\1', n).replace(' ', '_')
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save_manifest(m):
    out = json.dumps(m, ensure_ascii=False, indent=2) + '\n'
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(out, encoding='utf-8')
    (ARCHIVE / 'photo-manifest.json').write_text(out, encoding='utf-8')
def paragraphs(path):
    lines = Path(path).read_text(encoding='utf-8').replace('\r', '').split('\n')
    assert lines[0].startswith('# '), path
    return lines[0][2:], [l for l in lines[1:] if l.strip()]
def ratio(o): return o['w'] / o['h']
def orient(o): return 'V' if o['h'] > o['w'] * 1.05 else ('H' if o['w'] > o['h'] * 1.05 else 'S')


def caption_fields(p):
    hit = [c for c in FB_CAPTIONS if c[1] == p['chapter'] and c[2] == p['original_filename']]
    if not hit or not p['used']: return {}
    c = hit[0]
    return dict(caption_source=c[3], caption_from=f"facebook photo {c[0]} ({FB_POSTS[c[1]]})", **({'caption_note': c[4]} if len(c) > 4 else {}))


def shown_caption(p, m):
    text = p.get('caption_source')
    if not text: return None
    for a, b in m.get('caption_fixes', []): text = text.replace(a, b)
    return text


def captions():
    """Captions from FB_CAPTIONS into the manifest and data/photos; a row with a captioned photo becomes an exhibit row
    (labels under the photos). No new copies needed."""
    m = load(MANIFEST)
    for p in m['photos']:
        for k in ('caption_source', 'caption_approval', 'caption_from', 'caption_note'): p.pop(k, None)
        p.update(caption_fields(p))
    assert sum(1 for p in m['photos'] if p.get('caption_source')) == len(FB_CAPTIONS), 'a caption found no photo'
    m['caption_fixes'] = [list(f) for f in CAPTION_FIXES]
    m['text_policy'] = "Chapter texts verbatim from the owner's files; photo captions verbatim from her Facebook posts; display fixes of obvious typos in caption_fixes."
    captioned = {(p['chapter'], p['site_filename']) for p in m['photos'] if p.get('caption_source')}
    for c in m['chapters']:
        for b in c['blocks']:
            if b['kind'] in ('row', 'exhibit-row'):
                b['kind'] = 'exhibit-row' if any((c['slug'], n) in captioned for n in b['photos']) else 'row'
    data_file = ROOT / 'data/photos/poland-2026.json'
    data = load(data_file)
    for p in m['photos']:
        key = f"{p['chapter']}/{p['site_filename']}"
        if key in data:
            data[key].pop('caption', None)
            if shown_caption(p, m): data[key]['caption'] = shown_caption(p, m)
    data_file.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    save_manifest(m)
    print(f"{sum(1 for v in data.values() if v.get('caption'))} captions in data/photos/poland-2026.json.")


def plan():
    """Resolve the layout against the inventory: every file of every folder is used once or listed as unused."""
    inv = load(INVENTORY)
    byref = {}
    for c in CHAPTERS:
        for o in inv:
            if o['chapter_folder'] == c['folder']:
                byref[c['slug'], o['index']] = o
    problems, order = [], {}
    for c in CHAPTERS:
        seq = [c['hero']]
        for para, blocks in c['layout'].items():
            for kind, items in blocks:
                seq += items if isinstance(items, list) else [items]
        refs = [r if isinstance(r, tuple) else (c['slug'], r) for r in seq]
        order[c['slug']] = refs
        if len(refs) != len(set(refs)): problems.append(f"{c['slug']}: a photo is used twice")
        own = {k for k in byref if k[0] == c['slug']}
        used_here = {r for r in refs if r[0] == c['slug']}
        elsewhere = {r for o2 in CHAPTERS if o2 is not c for r in
                     [x if isinstance(x, tuple) else (o2['slug'], x) for b in o2['layout'].values() for k, it in b
                      for x in (it if isinstance(it, list) else [it])] if r[0] == c['slug']}
        unused = {(c['slug'], i) for i in c['unused']}
        missing = own - used_here - elsewhere - unused
        if missing: problems.append(f"{c['slug']}: not placed: {sorted(i for _, i in missing)}")
        if (used_here | unused) - own: problems.append(f"{c['slug']}: unknown numbers {sorted((used_here | unused) - own)}")
        if used_here & unused: problems.append(f"{c['slug']}: both used and unused {sorted(used_here & unused)}")
        if byref[c['slug'], c['hero']]['w'] <= byref[c['slug'], c['hero']]['h']: problems.append(f"{c['slug']}: hero is not horizontal")
        # layout rules
        for para, blocks in c['layout'].items():
            for kind, items in blocks:
                if kind not in ('r', 'x'): continue
                os_ = [orient(byref[r if isinstance(r, tuple) else (c['slug'], r)]) for r in items]
                if len(items) == 1 and os_[0] == 'V': problems.append(f"{c['slug']} p{para}: lone vertical {items}")
                if len(items) == 3 and os_.count('H') > 1: problems.append(f"{c['slug']} p{para}: three with {os_.count('H')} horizontal {items}")
                if len(items) > 3: problems.append(f"{c['slug']} p{para}: more than three in a row {items}")
            pairs = [(k, it) for k, it in blocks if k in ('r', 'x') and len(it) == 2]
            for (k1, a), (k2, b) in zip(blocks, blocks[1:]):
                if k1 in ('r', 'x') and k2 in ('r', 'x') and len(a) == 2 and len(b) == 2:
                    oa = ''.join(orient(byref[r if isinstance(r, tuple) else (c['slug'], r)]) for r in a)
                    ob = ''.join(orient(byref[r if isinstance(r, tuple) else (c['slug'], r)]) for r in b)
                    if oa in ('VH', 'HV') and oa == ob: problems.append(f"{c['slug']} p{para}: two {oa} rows in a row {a} {b}")
    return inv, byref, order, problems


def check():
    inv, byref, order, problems = plan()
    # the Drive folders still hold exactly the inventoried files
    on_disk = {}
    for c in CHAPTERS:
        for p in (ARCHIVE / c['folder']).iterdir():
            if p.is_file() and p.name.lower() != 'desktop.ini':
                on_disk[c['folder'], p.name] = p
    listed = {(o['chapter_folder'], o['name']) for o in inv}
    if set(on_disk) != listed:
        problems.append(f'Drive differs from inventory: extra {sorted(set(on_disk) - listed)[:5]}, missing {sorted(listed - set(on_disk))[:5]}')
    with ThreadPoolExecutor(8) as pool:
        digests = dict(zip(on_disk, pool.map(sha, on_disk.values())))
    for o in inv:
        if digests.get((o['chapter_folder'], o['name'])) != o['sha256']: problems.append(f"changed since inventory: {o['chapter_folder']}/{o['name']}")
    # sources: chapter texts and caption files are on Drive; captions are verbatim from the caption files
    for c in CHAPTERS:
        title, paras = paragraphs(SOURCES / c['source'])
        if title != c.get('source_title', c['title']): problems.append(f"{c['slug']}: source title {title!r}")
        if max(c['layout']) > len(paras): problems.append(f"{c['slug']}: layout refers to paragraph {max(c['layout'])} of {len(paras)}")
    print('\n'.join(problems) if problems else f'OK: {len(inv)} files, {sum(len(v) for v in order.values())} shown, layout rules hold.')
    return not problems


def archive():
    assert not MANIFEST.exists(), 'Archive already done; later stages read the manifest.'
    assert check(), 'Fix the problems first.'
    inv, byref, order, _ = plan()
    photos, chapters, sources, moves = [], [], [], []
    (ARCHIVE / 'Источники').mkdir(exist_ok=True)
    for n, c in enumerate(CHAPTERS, 1):
        title, paras = paragraphs(SOURCES / c['source'])
        src = ARCHIVE / 'Источники' / c['source']
        shutil.copyfile(SOURCES / c['source'], src)
        assert sha(src) == sha(SOURCES / c['source'])
        sources.append(dict(chapter=c['slug'], archive_name='Источники/' + c['source'], sha256=sha(src), title=title, paragraphs=paras))
        shown = {}
        for pos, ref in enumerate(order[c['slug']], 1):
            o = byref[ref]
            shown[ref] = dict(o=o, name=f"{pos:02d}_{o['name']}", folder=c['folder'], chapter=c['slug'], position=pos)
        for i, why in c['unused'].items():
            o = byref[c['slug'], i]
            shown[c['slug'], i] = dict(o=o, name='zz_не использовано_' + o['name'], folder=c['folder'], chapter=c['slug'], unused=why)
        for ref, s in shown.items():
            o = s['o']
            old, new = ARCHIVE / o['chapter_folder'] / o['name'], ARCHIVE / s['folder'] / s['name']
            assert sha(old) == o['sha256'] and not new.exists(), (old, new)
            if old.parent != new.parent: moves.append(dict(original_folder=o['chapter_folder'], to=f"{s['folder']}/{s['name']}"))
            old.rename(new)
            assert sha(new) == o['sha256']
            sn = site_name(o['name'])
            photos.append(dict(chapter=s['chapter'], inventory_ref=[ref[0], ref[1]], archive_name=f"{s['folder']}/{s['name']}",
                original_filename=o['name'], owner_folder=o['chapter_folder'], original_bytes=o['bytes'], original_sha256=o['sha256'],
                kind=o['kind'], w=o.get('w'), h=o.get('h'), exif_orientation=o.get('exif_orientation'), date_original=o.get('date_original'),
                onedrive_source=o.get('onedrive_source'), onedrive_sha256_matches=o.get('onedrive_sha256_matches'),
                used='unused' not in s, unused_reason=s.get('unused'), position=s.get('position'),
                site_filename=sn if 'unused' not in s else None, r2_key=f"{SLUG}/{s['chapter']}/{sn}" if 'unused' not in s else None,
))
        name_of = lambda r: site_name(byref[r if isinstance(r, tuple) else (c['slug'], r)]['name'])
        blocks = [dict(after_paragraph=p, kind={'r': 'row', 'x': 'exhibit-row', 'm': 'mosaic', 'v': 'video', 'b': 'beside'}[k],
                       photos=[name_of(r) for r in (it if isinstance(it, list) else [it])])
                  for p, bl in c['layout'].items() for k, it in bl]
        chapters.append(dict(slug=c['slug'], title=c['title'], weight=n * 10, date=c['date'], city=c['city'], places=c['places'],
                             folder=c['folder'], source='Источники/' + c['source'], hero_image=name_of(c['hero']), blocks=blocks))
    caption_sources = []
    for f in CAPTION_FILES:
        shutil.copyfile(SOURCES / f, ARCHIVE / 'Источники' / f)
        caption_sources.append(dict(archive_name='Источники/' + f, sha256=sha(ARCHIVE / 'Источники' / f)))
    cover = byref[TRIP_COVER['chapter'], TRIP_COVER['photo']]
    m = dict(schema_version=1, trip=SLUG, title='Наша Польша', contentDir='content/europe/poland/poland-2026',
        archive_root='Europe/2026 - Польша', created=datetime.now(timezone.utc).isoformat(),
        history=['Owner selected the photos into five chapter folders and wrote the texts and captions (Drive «Отчеты»), 24 Nov 2026.',
                 'Codex prepared the inventory, captions and a first paragraph assignment (script not committed, 24 Nov 2026).',
                 'Claude archived, laid out and published the draft from it, 24 Nov 2026 (scripts/prepare-poland-2026.py).'],
        text_policy='Chapter texts verbatim from the owner\'s files; captions are set by the captions stage.',
        sources=sources, caption_sources=caption_sources, moved_between_folders=moves,
        trip_cover=dict(chapter=TRIP_COVER['chapter'], site_filename=site_name(cover['name']), position=TRIP_COVER['position']),
        chapters=chapters, photos=photos, originals_verified=True, drive_sync_verified=False, r2_verified=False)
    save_manifest(m)
    print(f'Archived {len(photos)} originals ({sum(p["used"] for p in photos)} shown), {len(moves)} moved, {len(sources)} texts.')


def display():
    m = load(MANIFEST)
    assert m['drive_sync_verified'], 'Run check-drive-sync --write first.'
    data, copies = {}, []
    def make(p):
        src = ARCHIVE / p['archive_name']
        assert sha(src) == p['original_sha256'], src
        dest = ROOT / 'static/r2' / p['r2_key']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if p['kind'] == 'video':
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), *VIDEO_RECIPE, str(dest)], check=True)
            w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                            '-of', 'csv=p=0', str(dest)], capture_output=True, text=True, check=True).stdout.strip().split(','))
            recipe = dict(tool='ffmpeg', args=VIDEO_RECIPE, note='HEVC original -> H.264 for all browsers; rotation applied; metadata (GPS) dropped')
        else:
            from PIL import Image, ImageOps
            with Image.open(src) as raw:
                icc = raw.info.get('icc_profile')
                im = ImageOps.exif_transpose(raw).convert('RGB')
                assert (im.width, im.height) == (p['w'], p['h']), (src, im.size)
                im.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)
                im.save(dest, 'JPEG', quality=88, optimize=True, progressive=True, **({'icc_profile': icc} if icc else {}))
                w, h = im.size
            recipe = dict(tool='Pillow', exif_transpose=True, long_side_max=LONG_SIDE, no_upscale=True, jpeg_quality=88, exif_dropped=True)
        return p, dict(key=p['r2_key'], kind=p['kind'], archive_name=p['archive_name'], original_sha256=p['original_sha256'],
                       bytes=dest.stat().st_size, sha256=sha(dest), w=w, h=h, recipe=recipe)
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(make, [p for p in m['photos'] if p['used']]))
    for p, c in results:
        copies.append(c)
        if p['kind'] == 'video': continue
        entry = dict(w=c['w'], h=c['h'], source=p['archive_name'])
        if shown_caption(p, m): entry['caption'] = shown_caption(p, m)
        data[f"{p['chapter']}/{p['site_filename']}"] = entry
    (ROOT / 'data/photos/poland-2026.json').write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    m['r2'] = dict(bucket='family-travel-photos', base=BASE, copies=sorted(copies, key=lambda c: c['key']), verified=None)
    save_manifest(m)
    print(f'{len(copies)} copies ({sum(c["kind"] == "video" for c in copies)} videos), {sum(c["bytes"] for c in copies) / 1e6:.0f} MB.')
    posters()


def poster_key(video_key): return video_key[:-4] + '-poster.jpg'


def posters():
    """Stills for videos whose first frame is blurred: a frame of the video's screen copy, kept beside it on R2."""
    m = load(MANIFEST)
    copies = [c for c in m['r2']['copies'] if c['kind'] != 'poster']
    for c in list(copies):
        at = VIDEO_POSTERS.get(c['key'].split('/', 1)[1])
        if at is None: continue
        video, dest = ROOT / 'static/r2' / c['key'], ROOT / 'static/r2' / poster_key(c['key'])
        assert sha(video) == c['sha256']
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(at), '-i', str(video), '-frames:v', '1', '-q:v', '3', str(dest)], check=True)
        copies.append(dict(key=poster_key(c['key']), kind='poster', video_key=c['key'], archive_name=c['archive_name'],
                           original_sha256=c['original_sha256'], bytes=dest.stat().st_size, sha256=sha(dest), w=c['w'], h=c['h'],
                           recipe=dict(tool='ffmpeg', frame_at_seconds=at, of='screen copy of the video')))
    m['r2']['copies'] = sorted(copies, key=lambda c: c['key'])
    m['r2']['verified'] = None; m['r2_verified'] = False
    save_manifest(m)
    print(f"{sum(c['kind'] == 'poster' for c in copies)} video stills.")


def verify_r2():
    m = load(MANIFEST)
    def get(c):
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + urllib.request.quote(c['key']), headers={'User-Agent': 'family-blog-check'}), timeout=60) as r:
                body, ctype = r.read(), r.headers.get('Content-Type', '')
            ok = hashlib.sha256(body).hexdigest() == c['sha256'] and ctype == ('video/mp4' if c['kind'] == 'video' else 'image/jpeg')
            return c, ok, ctype
        except Exception as e:
            return c, False, repr(e)
    with ThreadPoolExecutor(12) as pool:
        res = list(pool.map(get, m['r2']['copies']))
    bad = [(c['key'], why) for c, ok, why in res if not ok]
    now = datetime.now(timezone.utc).isoformat()
    for c, ok, _ in res: c['public_verified'] = now if ok else False
    m['r2']['verified'] = now if not bad else False
    m['r2_verified'] = not bad
    save_manifest(m)
    print(f'{len(res) - len(bad)}/{len(res)} public copies match byte for byte.', *bad[:10], sep='\n')


def render():
    m = load(MANIFEST)
    TRIP.mkdir(parents=True, exist_ok=True)
    country = ROOT / 'content/europe/poland/_index.md'
    # the country page is a draft as long as the trip is, so that production never shows an empty country
    country.write_text(f'---\ntitle: "Польша"\ncountry: "Poland"\ncontinent: "Europe"\ndraft: {DRAFT}\n---\n', encoding='utf-8')
    cover = m['trip_cover']
    (TRIP / '_index.md').write_text(f'''---
title: "Наша Польша"
type: "trips"
trip_year: 2026
trip_start: "2026-11"
trip_end: "2026-11"
date: "2026-11-13"
continent: "Europe"
country: "Poland"
geo_countries:
  - poland
cover_where: "Вроцлав, Краков, Величка"
cover_title: "Наша Польша"
cover_when: "Ноябрь 2026"
cover_who: "Серёжа, Леля и Наташа"
cover_image: "{BASE}{SLUG}/{cover['chapter']}/{cover['site_filename']}"
cover_position: "{cover['position']}"
draft: {DRAFT}
---
''', encoding='utf-8')
    for c in m['chapters']:
        src = next(s for s in m['sources'] if s['chapter'] == c['slug'])
        title, paras = paragraphs(ARCHIVE / src['archive_name'])
        assert sha(ARCHIVE / src['archive_name']) == src['sha256'] and paras == src['paragraphs']
        after = {}
        for b in c['blocks']: after.setdefault(b['after_paragraph'], []).append(b)
        body = []
        for i, p in enumerate(paras, 1):
            para = '<p>' + html.escape(p, quote=False) + '</p>'
            blocks = after.get(i, [])
            if blocks and blocks[0]['kind'] == 'beside':
                body.append('{{< beside "' + blocks[0]['photos'][0] + '" >}}\n' + para + '\n{{< /beside >}}')
                blocks = blocks[1:]
            else:
                body.append(para)
            for b in blocks:
                names = ' '.join(b['photos'])
                if b['kind'] == 'row': body.append('{{< row "' + names + '" >}}')
                elif b['kind'] == 'exhibit-row': body.append('{{< exhibit-row "' + names + '" >}}')
                elif b['kind'] == 'mosaic': body.append('{{< mosaic "L:' + names + '" >}}')
                elif b['kind'] == 'video':
                    key = f"{SLUG}/{c['slug']}/{names}"
                    still = ' "' + BASE + poster_key(key) + '"' if any(r['key'] == poster_key(key) for r in m['r2']['copies']) else ''
                    body.append('{{< travel-video "' + BASE + key + '"' + still + ' >}}')
                else: raise ValueError(b)
        folder = TRIP / c['slug']
        folder.mkdir(exist_ok=True)
        places = ''.join('\n  - ' + p for p in c['places'])
        (folder / 'index.md').write_text(f'''---
title: {json.dumps(c['title'], ensure_ascii=False)}
chapter_kind: "part"
layout: "photo-story"
weight: {c['weight']}
city: {json.dumps(c['city'], ensure_ascii=False)}
places:{places}
hero_image: {json.dumps(c['hero_image'])}
date: "{c['date']}"
auto_gallery: false
draft: {DRAFT}
attractions: {json.dumps(ATTRACTIONS[c['slug']])}
---
''' + '\n\n'.join(body) + '\n', encoding='utf-8')
    print(f"Rendered {len(m['chapters'])} chapters, {sum(len(s['paragraphs']) for s in m['sources'])} paragraphs.")


def relayout():
    """Apply later changes of CHAPTERS (hero, blocks, titles) and TRIP_COVER to the archived trip: renumber the
    shown originals on Drive to the new page order (NN_), update the manifest and the sources in data/photos."""
    m = load(MANIFEST)
    _, byref, order, problems = plan()
    assert not problems, problems
    photos = {tuple(p['inventory_ref']): p for p in m['photos']}
    renames = []
    for c in CHAPTERS:
        for pos, ref in enumerate(order[c['slug']], 1):
            p = photos[ref]
            new = f"{p['archive_name'].split('/')[0]}/{pos:02d}_{p['original_filename']}"
            p['position'] = pos
            if new != p['archive_name']: renames.append((p, new))
    for p, new in renames:  # two steps, so that no new name meets an old one
        src = ARCHIVE / p['archive_name']
        assert sha(src) == p['original_sha256'], src
        src.rename(src.with_name('tmp_' + src.name))
    for p, new in renames:
        tmp = ARCHIVE / p['archive_name']
        tmp = tmp.with_name('tmp_' + tmp.name)
        dest = ARCHIVE / new
        assert not dest.exists(), dest
        tmp.rename(dest)
        assert sha(dest) == p['original_sha256'], dest
        for cp in m['r2']['copies']:
            if cp['archive_name'] == p['archive_name']: cp['archive_name'] = new
        p['archive_name'] = new
    kinds = {'r': 'row', 'x': 'exhibit-row', 'm': 'mosaic', 'v': 'video', 'b': 'beside'}
    for mc, c in zip(m['chapters'], CHAPTERS):
        assert mc['slug'] == c['slug']
        name_of = lambda r: site_name(byref[r if isinstance(r, tuple) else (c['slug'], r)]['name'])
        mc.update(title=c['title'], source_title=c.get('source_title', c['title']), hero_image=name_of(c['hero']),
                  blocks=[dict(after_paragraph=pa, kind=kinds[k], photos=[name_of(r) for r in (it if isinstance(it, list) else [it])])
                          for pa, bl in c['layout'].items() for k, it in bl])
    cover = byref[TRIP_COVER['chapter'], TRIP_COVER['photo']]
    m['trip_cover'] = dict(chapter=TRIP_COVER['chapter'], site_filename=site_name(cover['name']), position=TRIP_COVER['position'])
    data_file = ROOT / 'data/photos/poland-2026.json'
    data = load(data_file)
    for p in m['photos']:
        key = f"{p['chapter']}/{p['site_filename']}"
        if key in data: data[key]['source'] = p['archive_name']
    data_file.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    m['drive_sync_verified'] = False
    save_manifest(m)
    print(f'Renamed {len(renames)} originals on Drive; chapters, cover and sources updated. Run check-drive-sync --write next.')


def verify_site(site):
    """A built site (hugo -d <site>): texts verbatim and in order, each shown photo exactly once and from R2, captions."""
    m, problems, shown_total = load(MANIFEST), [], 0
    data = load(ROOT / 'data/photos/poland-2026.json')
    for c in m['chapters']:
        page = (Path(site) / 'europe/poland/poland-2026' / c['slug'] / 'index.html').read_text(encoding='utf-8')
        header = page[page.index('class="essay-header"'):page.index('class="essay-body"')]
        body = page[page.index('class="essay-body"'):page.index('class="essay-navigation"')]
        got = [html.unescape(re.sub(r'<[^>]+>', '', p)) for p in re.findall(r'<p>([\s\S]*?)</p>', body)]
        want = next(s for s in m['sources'] if s['chapter'] == c['slug'])['paragraphs']
        if got != want: problems.append(f"{c['slug']}: paragraphs differ ({len(got)} on page, {len(want)} in source)")
        links = re.findall(r'href="([^"]+\.jpg)"[^>]*data-photo-lightbox', header + body)
        videos = re.findall(r'<source src="([^"]+\.mp4)"', body)
        expect = [BASE + p['r2_key'] for p in m['photos'] if p['used'] and p['chapter'] == c['slug']]
        exp_photos = sorted(u for u in expect if u.endswith('.jpg')); exp_videos = sorted(u for u in expect if u.endswith('.mp4'))
        if sorted(links) != exp_photos:
            problems.append(f"{c['slug']}: photos differ: missing {sorted(set(exp_photos) - set(links))[:3]}, extra {sorted(set(links) - set(exp_photos))[:3]}, repeated {len(links) - len(set(links))}")
        if sorted(videos) != exp_videos: problems.append(f"{c['slug']}: videos differ")
        if any(re.search(r'drive\.google|googleusercontent', u) for u in re.findall(r'(?:src|href)="([^"]+)"', header + body)):
            problems.append(f"{c['slug']}: Drive URL on the page")
        for k, v in data.items():
            if k.startswith(c['slug'] + '/') and v.get('caption') and html.escape(v['caption'], quote=False) not in page and v['caption'] not in html.unescape(page):
                problems.append(f'{k}: caption not on the page')
        shown_total += len(links) + len(videos)
    trip = (Path(site) / 'europe/poland/poland-2026/index.html').read_text(encoding='utf-8')
    cover = BASE + f"{SLUG}/{m['trip_cover']['chapter']}/{m['trip_cover']['site_filename']}"
    if cover not in trip: problems.append('trip cover not on the trip page')
    print('\n'.join(problems) if problems else f"OK: {len(m['chapters'])} chapters, {sum(len(s['paragraphs']) for s in m['sources'])} paragraphs verbatim, {shown_total} photos and videos each once from R2, trip cover from R2.")


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if stage == 'verify-site': verify_site(sys.argv[2])
    else: {'check': check, 'archive': archive, 'display': display, 'posters': posters, 'captions': captions, 'relayout': relayout, 'verify-r2': verify_r2, 'render': render}[stage]()
