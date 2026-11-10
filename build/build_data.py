#!/usr/bin/env python3
"""Builds ../data.js for the India bookstore map.

Inputs (paths passed as arguments):
  1. Overpass JSON of shop=books / book-ish stationery shops in India
  2. Overpass JSON of aeroway=terminal in India
  3. GeoNames cities5000.zip
  4. GeoNames admin1CodesASCII.txt
  5. output path for data.js

Curated entries (CURATED below) carry hand-written blurbs. Everything else
comes from OpenStreetMap with a short description derived from its tags.
"""
import io, json, math, re, sys, time, urllib.parse, urllib.request, zipfile

osm_path, aero_path, cities_zip, admin_path, out_path = sys.argv[1:6]
SITES = {}
if "--sites" in sys.argv:  # output of the website liveness check: [{url, code, ig}]
    for x in json.load(open(sys.argv[sys.argv.index("--sites") + 1])):
        SITES[x["url"]] = x
GEOCODE = "--no-geocode" not in sys.argv


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("'", "")).strip()


# ---------- gazetteer ----------
admin = {}
for line in open(admin_path, encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    admin[p[0]] = p[1]
STATE_FIX = {"NCT": "Delhi", "National Capital Territory of Delhi": "Delhi", "Orissa": "Odisha",
             "Uttaranchal": "Uttarakhand", "Pondicherry": "Puducherry",
             "Dadra and Nagar Haveli and Daman and Diu": "Dadra & Nagar Haveli and Daman & Diu"}
CITY_FIX = {"Bengaluru": "Bengaluru", "Bangalore": "Bengaluru", "Calcutta": "Kolkata", "Bombay": "Mumbai",
            "Madras": "Chennai", "Cochin": "Kochi", "Trivandrum": "Thiruvananthapuram", "Panjim": "Panaji",
            "Gurgaon": "Gurugram", "Mysore": "Mysuru", "Mangalore": "Mangaluru", "Pondicherry": "Puducherry",
            "Benares": "Varanasi", "Simla": "Shimla", "Poona": "Pune", "Baroda": "Vadodara"}
cities = []
with zipfile.ZipFile(cities_zip) as z:
    for line in io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"):
        p = line.split("\t")
        if p[8] not in ("IN", "NP", "BT", "BD", "PK", "CN", "MM", "LK"):
            continue
        st = admin.get(p[8] + "." + p[10], "")
        cities.append((float(p[4]), float(p[5]), CITY_FIX.get(p[2], p[2]), STATE_FIX.get(st, st), p[8], int(p[14] or 0)))
grid = {}
for c in cities:
    grid.setdefault((int(c[0] * 2), int(c[1] * 2)), []).append(c)


def place(lat, lon):
    """Nearest sizeable Indian place; None if the point is closer to a foreign town with no Indian one near."""
    best_in = best_any = None
    gx, gy = int(lat * 2), int(lon * 2)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for c in grid.get((gx + dx, gy + dy), []):
                d = hav(lat, lon, c[0], c[1])
                # nudge towards bigger places so suburbs resolve to their city
                score = d - min(12, math.log10(max(c[5], 1000)) * 2.2 - 6.6) if c[5] > 1000 else d
                if best_any is None or d < best_any[0]:
                    best_any = (d, c)
                if c[4] == "IN" and (best_in is None or score < best_in[0]):
                    best_in = (score, c, d)
    if best_in is None:
        return None
    if best_any[1][4] != "IN" and best_in[2] > 30:
        return None
    return best_in[1][2], best_in[1][3]


# ---------- curated ----------
# (name, match key, city, state, type, lat, lon, blurb, is_place_not_shop)
C = [
 ("Bahrisons Booksellers", "bahrisons", "New Delhi", "Delhi", "independent", 28.6003, 77.2270,
  "Khan Market fixture since 1953, started by a family that arrived after Partition. Known for sharp curation of literary fiction, history and politics, and for knowing its regulars by name."),
 ("The Bookshop Inc.", "bookshop inc", "New Delhi", "Delhi", "independent", 28.5846, 77.2262,
  "Descendant of The Bookshop that opened in Jor Bagh in 1970. A small room, hand-picked fiction, and staff who will tell you what to read next."),
 ("Midland Book Shop", "midland", "New Delhi", "Delhi", "independent", 28.5459, 77.2040,
  "Floor-to-ceiling stacks in Aurobindo Place, and a standing discount on nearly everything. The Baig family has run Midland shops in Delhi since the 1970s."),
 ("Faqir Chand & Sons", "faqir chand", "New Delhi", "Delhi", "independent", 28.6001, 77.2266,
  "The oldest shop in Khan Market, open since 1951. Narrow aisles, towers of books, and very little that has changed in decades."),
 ("Jain Book Agency", "jain book agency", "New Delhi", "Delhi", "academic", 28.6328, 77.2197,
  "Connaught Place specialist in law books, bare acts and Government of India publications. Where Delhi's lawyers and civil-service aspirants shop."),
 ("Oxford Bookstore, Connaught Place", "oxford book", "New Delhi", "Delhi", "chain", 28.6315, 77.2206,
  "Delhi outpost of the Kolkata chain, with the Cha Bar tea room inside. Strong on Indian writing in English, design and travel."),
 ("Daryaganj Sunday Book Market", None, "Delhi", "Delhi", "secondhand", 28.6418, 77.2380,
  "Weekly second-hand book bazaar, now held at Mahila Haat near Delhi Gate after moving off the Daryaganj pavements in 2019. Books sold by the stack and sometimes by the kilo.", 1),
 ("May Day Bookstore", "may day", "New Delhi", "Delhi", "independent", 28.6517, 77.1583,
  "Run by LeftWord Books in Shadipur, next to Studio Safdar. Left politics, labour history, theatre, and a big second-hand section."),
 ("Kitab Khana", "kitab khana", "Mumbai", "Maharashtra", "independent", 18.9322, 72.8330,
  "Set in the 19th-century Somaiya Bhavan at Flora Fountain, with wooden mezzanines and a cafe. Unusually deep shelves in Hindi, Marathi, Gujarati and Urdu alongside English."),
 ("Trilogy by The Eternal Library", "trilogy", "Mumbai", "Maharashtra", "independent", 19.0606, 72.8300,
  "Half bookshop, half lending library in Bandra. Known for a tightly edited selection and for stocking small presses that other shops skip."),
 ("Title Waves", "title waves", "Mumbai", "Maharashtra", "independent", 19.0607, 72.8347,
  "One of Mumbai's largest standalone bookshops, in Bandra West. Roomy, well lit, with a strong children's section and regular author events."),
 ("Flora Fountain pavement booksellers", None, "Mumbai", "Maharashtra", "secondhand", 18.9325, 72.8317,
  "Street stalls around Flora Fountain and along the Fort arcades selling second-hand paperbacks, textbooks and old magazines. Bargaining expected.", 1),
 ("Blossom Book House", "blossom", "Bengaluru", "Karnataka", "secondhand", 12.9750, 77.6046,
  "Church Street institution since 2002, with several floors of second-hand and new books. People come with a list and leave with a bag of things that weren't on it."),
 ("The Bookworm", "bookworm", "Bengaluru", "Karnataka", "secondhand", 12.9747, 77.6050,
  "Blossom's friendly rival on Church Street, in an old bungalow. New and used books side by side, and a buy-back scheme regulars swear by."),
 ("Higginbothams, MG Road", "higginbotham", "Bengaluru", "Karnataka", "chain", 12.9755, 77.6030,
  "A 1905 colonial building on MG Road, and one of Bengaluru's oldest shops of any kind. Come for the building as much as the books."),
 ("Gangarams Book Bureau", "gangaram", "Bengaluru", "Karnataka", "independent", 12.9745, 77.6055,
  "A Bengaluru name for decades, on MG Road before it moved to Church Street. Known for textbooks, technical titles and a broad general range."),
 ("Select Book Shop", "select book", "Bengaluru", "Karnataka", "secondhand", 12.9735, 77.6075,
  "Founded in 1945 and tucked off Brigade Road. Rare, antiquarian and out-of-print books, run by a family that knows where every one of them is."),
 ("Champaca Bookstore", "champaca", "Bengaluru", "Karnataka", "independent", 12.9890, 77.5940,
  "A women-run bookshop, cafe and children's library among the treetops off Edward Road. Known for translations, independent presses and a book subscription."),
 ("Atta Galatta", "atta galatta", "Bengaluru", "Karnataka", "independent", 12.9700, 77.6400,
  "Bookshop and performance space built around Indian-language writing. Hosts readings, plays and the Bangalore Poetry Festival crowd."),
 ("Sapna Book House, Gandhinagar", "sapna", "Bengaluru", "Karnataka", "chain", 12.9770, 77.5770,
  "Flagship of the Karnataka chain and among the largest book stores in the country. Several floors covering textbooks, Kannada titles, fiction and stationery."),
 ("Lightroom Bookstore", "lightroom", "Bengaluru", "Karnataka", "independent", 12.9990, 77.6230,
  "A children's bookshop in Cooke Town. Picture books and young-adult titles chosen by people who have read them."),
 ("Ankita Pustaka", "ankita", "Bengaluru", "Karnataka", "independent", 12.9450, 77.5710,
  "Gandhi Bazaar's Kannada bookshop and publisher. The place to find contemporary Kannada fiction and essays."),
 ("Higginbothams, Anna Salai", "higginbotham", "Chennai", "Tamil Nadu", "chain", 13.0640, 80.2700,
  "Open since 1844 and widely regarded as India's oldest bookshop still trading. The white colonial building on Mount Road is a Chennai landmark."),
 ("Tulika Bookstore", "tulika", "Chennai", "Tamil Nadu", "independent", 13.0350, 80.2530,
  "Shopfront of the children's publisher Tulika in Alwarpet. Picture books in English and many Indian languages, often the same story in several."),
 ("Odyssey, Adyar", "odyssey", "Chennai", "Tamil Nadu", "chain", 13.0060, 80.2570,
  "The Adyar original of a South Indian chain. Books share the floor with music, toys and gifts."),
 ("College Street (Boi Para)", None, "Kolkata", "West Bengal", "secondhand", 22.5750, 88.3635,
  "Often called the largest second-hand book market in the world. Hundreds of stalls and publishers' shops line the street between Presidency and Calcutta University.", 1),
 ("Oxford Bookstore, Park Street", "oxford book", "Kolkata", "West Bengal", "chain", 22.5535, 88.3520,
  "The Park Street original, trading for about a century. Wooden gallery, Cha Bar upstairs, and home base of the Apeejay Kolkata Literary Festival."),
 ("Dasgupta & Co.", "dasgupta", "Kolkata", "West Bengal", "academic", 22.5745, 88.3630,
  "On College Street since 1886, the oldest bookshop in Kolkata. Academic and reference titles stacked to the ceiling."),
 ("Seagull Bookstore", "seagull", "Kolkata", "West Bengal", "independent", 22.5330, 88.3450,
  "Bookshop of the publisher Seagull Books in Bhowanipore. Translated literature, theatre, cinema and art."),
 ("Story, Salt Lake", "story", "Kolkata", "West Bengal", "independent", 22.5712, 88.4128,
  "Kolkata's big general bookshop, on Elgin Road from 2004 until 2023 and now in a smaller space at Primarc Square, opposite Salt Lake Stadium. Bengali and English titles, gifts and a cafe."),
 ("Earthcare Books", "earthcare", "Kolkata", "West Bengal", "independent", 22.5440, 88.3530,
  "Small shop and publisher on Middleton Street focused on ecology, organic farming and development."),
 ("Abids Sunday Book Market", None, "Hyderabad", "Telangana", "secondhand", 17.3920, 78.4760,
  "Every Sunday the shuttered shopfronts of Abids become a second-hand book market. Novels, exam guides and old magazines spread out on the pavement.", 1),
 ("Pagdandi Books Chai Cafe", "pagdandi", "Pune", "Maharashtra", "independent", 18.5590, 73.7890,
  "Bookshop cafe in Baner started by two travellers. Known for open mics, writing workshops and long stays over chai."),
 ("Appa Balwant Chowk book market", None, "Pune", "Maharashtra", "academic", 18.5175, 73.8540,
  "Pune's textbook district, known as ABC. Dozens of shops selling school, engineering and exam-prep books, new and used.", 1),
 ("Literati Bookshop & Cafe", "literati", "Calangute", "Goa", "independent", 15.5380, 73.7620,
  "A bookshop in an old Goan house with a garden. New and second-hand books, readings, and a place to sit away from the beach."),
 ("The Dogears Bookshop", "dogears", "Margao", "Goa", "independent", 15.2830, 73.9620,
  "South Goa's favourite small bookshop. New and pre-owned books, and a strong shelf of Goan writing."),
 ("Broadway Book Centre", "broadway", "Panaji", "Goa", "independent", 15.4980, 73.8280,
  "The largest bookshop in Goa, in central Panaji. Publishes and stocks more books about Goa than anyone else."),
 ("Singbal's Book House", "singbal", "Panaji", "Goa", "independent", 15.4985, 73.8290,
  "Opposite Panaji's church since 1936. Newspapers, magazines and Goa titles in a corner shop that has barely changed."),
 ("DC Books, Kottayam", "dc books", "Kottayam", "Kerala", "chain", 9.5900, 76.5220,
  "Home branch of Kerala's biggest publisher and bookshop chain. The widest range of Malayalam literature you will find in one place."),
 ("Modern Book Centre", "modern book", "Thiruvananthapuram", "Kerala", "independent", 8.4920, 76.9490,
  "Thiruvananthapuram's long-running English-language bookshop. Trusted for fiction, academic titles and special orders."),
 ("Idiom Booksellers", "idiom", "Kochi", "Kerala", "independent", 9.9660, 76.2420,
  "Small Fort Kochi shop for travellers. Books on Kerala, Indian fiction and second-hand paperbacks left by earlier visitors."),
 ("Rachna Books", "rachna", "Gangtok", "Sikkim", "independent", 27.3350, 88.6150,
  "Gangtok's independent bookshop, with a cafe and a guest room upstairs. Strong on the Himalaya and the Northeast, and a regular host of readings and gigs."),
 ("Oxford Book & Stationery Co.", "oxford", "Darjeeling", "West Bengal", "independent", 27.0430, 88.2670,
  "On Chowrasta in Darjeeling, unrelated to the chain. The best selection anywhere on the Himalaya, tea and Tibet."),
 ("Cambridge Book Depot", "cambridge", "Mussoorie", "Uttarakhand", "independent", 30.4550, 78.0750,
  "Mall Road shop where Ruskin Bond signed books on Saturday afternoons for years. Stocks everything he has written."),
 ("The English Book Depot", "english book", "Dehradun", "Uttarakhand", "independent", 30.3250, 78.0440,
  "Dehradun institution on Rajpur Road since the 1920s. General books downstairs, coffee next door."),
 ("Gulshan Books, Residency Road", "gulshan", "Srinagar", "Jammu and Kashmir", "independent", 34.0712, 74.8140,
  "Srinagar's best-known bookseller and publisher, with one of the largest ranges of books on Kashmir. Its famous shop on an island in Dal Lake closed in 2022 when the lease ended."),
 ("Universal Booksellers", "universal", "Lucknow", "Uttar Pradesh", "independent", 26.8500, 80.9460,
  "Hazratganj mainstay since 1938. Lucknow's biggest general bookshop, strong on the city's own history."),
 ("Harmony, The Book Shop", "harmony", "Varanasi", "Uttar Pradesh", "independent", 25.2890, 83.0060,
  "A small, carefully chosen shop at Assi Ghat. Indian philosophy, religion, music and literature for visitors who want depth."),
 ("Pilgrims Book House", "pilgrims", "Varanasi", "Uttar Pradesh", "religious", 25.3010, 83.0030,
  "Publisher and bookseller specialising in Hinduism, Buddhism, yoga and the Himalaya, with a sister shop in Kathmandu."),
 ("Maria Brothers", "maria brothers", "Shimla", "Himachal Pradesh", "secondhand", 31.1040, 77.1740,
  "Antiquarian shop on the Mall in Shimla. Rare books, old maps and prints from the Raj."),
 ("Capital Book Depot", "capital book", "Chandigarh", "Chandigarh", "independent", 30.7400, 76.7820,
  "Sector 17 landmark dating to Chandigarh's early years. A broad general range and reliable recommendations."),
 ("The Browser Library & Bookstore", "browser", "Chandigarh", "Chandigarh", "independent", 30.7400, 76.7950,
  "A lending library with a bookshop attached in Sector 8. Members borrow, everyone else buys."),
 ("SABDA, Sri Aurobindo Ashram", "sabda", "Puducherry", "Puducherry", "religious", 11.9370, 79.8350,
  "The Ashram's book distribution arm. Works of Sri Aurobindo and the Mother in many languages."),
 ("Lawyer's Book Stall", "lawyers book", "Guwahati", "Assam", "independent", 26.1860, 91.7450,
  "In Panbazar since the 1940s and a publisher as well as a bookseller. Assam's go-to for Assamese literature."),
 ("Ladakh Book Shop", "ladakh book", "Leh", "Ladakh", "independent", 34.1640, 77.5850,
  "Upstairs in Leh's main bazaar. Maps, trekking guides and the best shelf of books on Ladakh and Tibet."),
 ("Bookworm", "bookworm", "Dharamshala", "Himachal Pradesh", "independent", 32.2380, 76.3240,
  "McLeod Ganj's small bookshop. Tibetan history, Buddhism and travel writing."),
 ("Higginbothams, Ooty", "higginbotham", "Ooty", "Tamil Nadu", "chain", 11.4110, 76.7000,
  "A hill-station branch of the old Madras bookseller, in a low colonial building near Charing Cross."),
]

# Links confirmed in November 2026: (website, instagram handle)
LINKS = {
 "Bahrisons Booksellers": ("https://www.booksatbahri.com", "bahrisons_booksellers"),
 "The Bookshop Inc.": ("", "thebookshopinc"),
 "Faqir Chand & Sons": ("", "faqirchandbookstore"),
 "Jain Book Agency": ("https://www.jainbookagency.com", ""),
 "May Day Bookstore": ("https://leftword.com", "leftwordbooks"),
 "Kitab Khana": ("https://www.kitabkhana.in", "kitabkhanabooks"),
 "Trilogy by The Eternal Library": ("https://www.theeternallibrary.com", ""),
 "Title Waves": ("https://titlewaves.in", ""),
 "Oxford Bookstore, Connaught Place": ("https://oxfordbookstore.com", "oxfordbookstores"),
 "Oxford Bookstore, Park Street": ("https://oxfordbookstore.com", "oxfordbookstores"),
 "Blossom Book House": ("https://www.blossombookhouse.in", "blossombookhouse"),
 "Gangarams Book Bureau": ("https://gangaramsbookbureau.com", "gangaramsbookbureau1977"),
 "Champaca Bookstore": ("https://champaca.in", "champacabooks"),
 "Atta Galatta": ("https://www.attagalatta.com", "attagalatta"),
 "Sapna Book House, Gandhinagar": ("https://www.sapnaonline.com", ""),
 "Lightroom Bookstore": ("https://www.lightroombookstore.com", ""),
 "Ankita Pustaka": ("https://ankitapustaka.com", ""),
 "Tulika Bookstore": ("https://www.tulikabooks.com", "tulikabooks"),
 "Odyssey, Adyar": ("https://odyssey.in", ""),
 "Seagull Bookstore": ("https://seagullbooks.org", ""),
 "Earthcare Books": ("https://earthcarebooks.com", ""),
 "Pagdandi Books Chai Cafe": ("https://pagdandi.org", "pagdandi"),
 "Literati Bookshop & Cafe": ("https://www.literatigoa.com", "literatigoa"),
 "The Dogears Bookshop": ("https://thedogearsbookshop.com", "the_dogears_bookshop"),
 "DC Books, Kottayam": ("https://dcbooks.com", "dcbooks"),
 "Modern Book Centre": ("https://www.modernbookcentre.com", ""),
 "Rachna Books": ("https://rachnabooks.com", "rachnabooks"),
 "The English Book Depot": ("https://englishbookdepot.com", "englishbookdepot"),
 "Universal Booksellers": ("https://universalbooksellers.com", ""),
 "SABDA, Sri Aurobindo Ashram": ("https://www.sabda.in", ""),
}
# Searched, but no current evidence either way.
UNCONFIRMED = {"Maria Brothers", "Pilgrims Book House", "Oxford Book & Stationery Co.", "Capital Book Depot",
               "The Browser Library & Bookstore"}
# Not searched individually: treated as unconfirmed unless OpenStreetMap also has them.
UNSEARCHED = {"Bookworm", "Higginbothams, Ooty", "Harmony, The Book Shop", "Idiom Booksellers", "Singbal's Book House",
              "Ladakh Book Shop", "The Bookworm", "Select Book Shop", "Higginbothams, MG Road", "Higginbothams, Anna Salai",
              "Lightroom Bookstore", "Seagull Bookstore", "Earthcare Books", "Modern Book Centre", "Universal Booksellers",
              "SABDA, Sri Aurobindo Ashram", "Ankita Pustaka", "Tulika Bookstore", "Trilogy by The Eternal Library",
              "Title Waves", "Sapna Book House, Gandhinagar", "Jain Book Agency", "DC Books, Kottayam"}
CONFIRMED_ANYWAY = {"The Bookworm", "Select Book Shop", "Lightroom Bookstore", "Seagull Bookstore", "Earthcare Books",
                    "Modern Book Centre", "Universal Booksellers", "SABDA, Sri Aurobindo Ashram", "Ankita Pustaka",
                    "Tulika Bookstore", "Trilogy by The Eternal Library", "Title Waves", "Sapna Book House, Gandhinagar",
                    "Jain Book Agency", "DC Books, Kottayam"}  # live own website or recent press
BOOK_WORD = r"book|pustak|granth|kitab|library|novel|publication|prakashan"
NOT_A_BOOKSHOP = r"cool drinks|photostat|bakery|tailor|restaurant|pharmacy|salon|juice|tea stall|cyber|travels|mobile"

CHAINS = [
 (r"crossword", "Crossword", "Branch of India's largest bookshop chain. Bestsellers, children's books, stationery and gifts."),
 (r"higginbotham", "Higginbothams", "Branch of the bookseller founded in Madras in 1844, India's oldest. General books and stationery."),
 (r"sapna", "Sapna Book House", "Branch of Karnataka's big book retailer. Textbooks, Kannada and English titles, stationery."),
 (r"oxford book ?store", "Oxford Bookstore", "Branch of the Kolkata-born chain. Indian writing in English, with a Cha Bar in larger shops."),
 (r"\blandmark\b", "Landmark", "Branch of the Chennai-born chain. Books alongside toys, music and stationery."),
 (r"starmark", "Starmark", "Large-format chain store. Books, toys, stationery and gifts under one roof."),
 (r"\bd ?c books", "DC Books", "Branch of Kerala's biggest publisher-bookseller. Malayalam literature in depth."),
 (r"current books", "Current Books", "Kerala bookshop chain linked to DC Books. Malayalam fiction and non-fiction."),
 (r"mathrubhumi", "Mathrubhumi Books", "Bookshop of the Mathrubhumi newspaper group. Malayalam titles from its own press and others."),
 (r"national book stall|\bnbs\b", "National Book Stall", "Outlet of Kerala's writers' cooperative (SPCS). Malayalam literature at member prices."),
 (r"\bom book", "Om Book Shop", "North Indian chain with mall and market shops. Popular fiction, children's books and coffee-table titles."),
 (r"odyssey", "Odyssey", "South Indian leisure chain. Books, music, toys and gifts."),
 (r"h ?& ?c stores|h and c stores", "H&C Stores", "Kerala chain of book and stationery stores. Textbooks, guides and school supplies."),
 (r"just ?books", "JustBooks", "Branch of a membership lending library chain. Borrow rather than buy."),
 (r"kunzum", "Kunzum", "Delhi-NCR chain of bookshop cafes. Coffee, events and a curated general range."),
 (r"himalaya book world", "Himalaya Book World", "Hyderabad chain. Bestsellers, academic titles and discounts."),
 (r"prajashakti", "Prajasakti Book House", "Telugu publisher's bookshop. Progressive and left literature in Telugu."),
 (r"visalaandhra|vishalandhra|visalandhra", "Visalaandhra", "Telugu publisher's bookshop chain. Telugu literature and textbooks."),
 (r"nava ?karnataka", "Navakarnataka", "Kannada publisher's bookshop. Kannada literature, science and progressive writing."),
 (r"national book trust|\bnbt\b", "National Book Trust", "Government publisher's outlet. Affordable books in many Indian languages."),
 (r"teksons", "Teksons", "Delhi family of neighbourhood bookshops. General books, magazines and stationery."),
 (r"bahrisons", "Bahrisons", "Branch of the Khan Market bookseller. Well-chosen fiction and non-fiction."),
 (r"full circle", "Full Circle", "Delhi bookshop with a cafe. Spirituality, fiction and gifts."),
 (r"reader'?s delight", "Reader's Delight", "Small regional chain. General books and stationery."),
]
TRANSIT = r"w ?h ?smith|\brelay\b|wheeler|airport|railway"
RELIG = (r"gita ?press|geeta ?press|islam|quran|bible|christian|gospel|ramakrishna|iskcon|chinmaya|pauline|"
         r"st\.? ?pauls|catholic|\bsikh|gurbani|buddhis|dharm|jain granth|vedic|vedant|spiritual|yoga|ashram|"
         r"satsang|theosoph|krishna|masjid|church|holy|sai baba|osho|swami")
SECOND = r"old book|second ?hand|used book|pre ?owned|preloved|antiquar|rare book|kabadi|raddi"
STATIONER = r"station[ae]r|xerox|photo ?copy|\bpens?\b|paper mart|general store|gift|fancy|novelt"
ACADEMIC = (r"depot|depo\b|text ?book|school|college|universit|academic|student|educat|exam|competit|"
            r"law book|legal|medical|technical|engineering|scientific|science|vidya|shiksha|career|tutorial|"
            r"guide|notes|publication|prakashan|publisher")

GENERIC = {
 "independent": ["Neighbourhood bookshop in {c}.", "Local bookshop serving {c}.", "General bookshop in {c}."],
 "stationery": ["Books and stationery under one roof in {c}.", "Stationery shop that also sells books, in {c}."],
 "academic": ["Textbooks, guides and exam-prep titles in {c}.", "Academic and school books in {c}."],
 "secondhand": ["Second-hand and used books in {c}."],
 "religious": ["Religious and spiritual titles in {c}."],
 "transit": ["Travel-hub book stall in {c}. Paperbacks, magazines and newspapers for the journey."],
 "chain": ["Chain bookshop in {c}."],
}
BOOKS_TAG = {"academic": "academic titles", "children": "children's books", "religion": "religious books",
             "comic": "comics", "antiquarian": "antiquarian books", "newspaper": "newspapers", "general": "general books"}


def tidy_name(n):
    n = re.sub(r"\s+", " ", n).strip()
    letters = [ch for ch in n if ch.isalpha()]
    if letters and (all(ch.isupper() for ch in letters) or all(ch.islower() for ch in letters)) and n.isascii():
        small = {"and", "of", "the", "for", "in", "n"}
        w = n.lower().split(" ")
        n = " ".join(x if (i and x in small) else (x.upper() if len(x) <= 3 and "." in x else x[:1].upper() + x[1:]) for i, x in enumerate(w))
    return n


def classify(name, tags, near_terminal):
    nn = name.lower()
    if near_terminal or re.search(TRANSIT, nn):
        return "transit", None
    for pat, brand, blurb in CHAINS:
        if re.search(pat, nn) or re.search(pat, (tags.get("brand", "") + " " + tags.get("operator", "")).lower()):
            return "chain", (brand, blurb)
    if tags.get("second_hand") in ("yes", "only") or re.search(SECOND, nn) or "antiquarian" in tags.get("books", ""):
        return "secondhand", None
    if re.search(RELIG, nn) or "religion" in tags.get("books", ""):
        return "religious", None
    if tags.get("shop") == "stationery" or re.search(STATIONER, nn):
        return "stationery", None
    if re.search(ACADEMIC, nn) or "academic" in tags.get("books", ""):
        return "academic", None
    return "independent", None


# ---------- OSM ----------
terminals = []
for e in json.load(open(aero_path))["elements"]:
    la, lo = e.get("lat") or e.get("center", {}).get("lat"), e.get("lon") or e.get("center", {}).get("lon")
    if la:
        terminals.append((la, lo))

rows, seen, delisted = [], [], 0
for e in json.load(open(osm_path))["elements"]:
    t = e.get("tags", {})
    raw = t.get("name")
    la, lo = e.get("lat") or e.get("center", {}).get("lat"), e.get("lon") or e.get("center", {}).get("lon")
    if not raw or la is None:
        continue
    name, alt = raw, ""
    if not raw.isascii():
        en = t.get("name:en") or t.get("int_name")
        if en:
            name, alt = en, raw
    name = tidy_name(name)
    if len(norm(name)) < 3 and name.isascii():
        continue
    if re.search(NOT_A_BOOKSHOP, name.lower()) and not re.search(r"book|pustak|granth|kitab", name.lower()):
        continue
    pl = place(la, lo)
    if pl is None:
        continue
    k = norm(name)
    if any(k == s[0] and hav(la, lo, s[1], s[2]) < 0.08 for s in seen):
        continue
    seen.append((k, la, lo))
    near = any(abs(la - a) < 0.01 and abs(lo - b) < 0.01 and hav(la, lo, a, b) < 0.25 for a, b in terminals)
    typ, chain = classify(name, t, near)
    # De-list shops that are stationers first: tagged shop=stationery on OpenStreetMap, or tagged as a
    # bookshop but with a stationery-style name and no book word in it. "Books & Stationery" hybrids stay.
    if t.get("shop") == "stationery" or (typ == "stationery" and not re.search(BOOK_WORD, name.lower())):
        delisted += 1
        continue
    city, state = pl
    desc = (t.get("description") or "").strip()
    if chain:
        blurb = chain[1]
    elif typ == "transit" and re.search(r"wheeler", name.lower()):
        blurb = "A. H. Wheeler stall, the railway-platform bookseller found at stations across North India since 1877."
    elif typ == "transit" and re.search(r"w ?h ?smith|relay", name.lower()):
        blurb = "Airport and travel-retail bookshop. Bestsellers, magazines and something for the flight."
    elif 25 < len(desc) < 220 and desc.isascii():
        blurb = desc if desc[-1] in ".!?" else desc + "."
    else:
        opts = GENERIC[typ]
        blurb = opts[(e["id"] // 7) % len(opts)].format(c=city)
        extra = [BOOKS_TAG[b] for b in re.split(r"[;,]\s*", t.get("books", "")) if b in BOOKS_TAG]
        if extra:
            blurb += " Tagged for " + ", ".join(extra) + "."
    addr = ", ".join(x for x in [
        " ".join(x for x in [t.get("addr:housenumber"), t.get("addr:street")] if x),
        t.get("addr:suburb") or t.get("addr:place"), t.get("addr:postcode")] if x)
    web = t.get("website") or t.get("contact:website") or ""
    if web and not web.startswith("http"):
        web = "https://" + web
    ig = (t.get("contact:instagram") or t.get("instagram") or "").strip()
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", web)
    if m:
        ig, web = ig or m.group(1), ""
    ig = re.sub(r"^.*instagram\.com/", "", ig).strip("@/ ").split("/")[0].split("?")[0]
    fb = (t.get("contact:facebook") or t.get("facebook") or "").strip()
    if "facebook.com" in web:
        fb, web = fb or web, ""
    if fb and not fb.startswith("http"):
        fb = "https://www.facebook.com/" + fb.lstrip("@/")
    site = SITES.get(web)
    if site:
        if site["code"] in ("000", "404", "410", "ERR"):
            web = ""  # dead link
        elif not ig and len(site.get("ig", [])) == 1:
            ig = site["ig"][0]
    year = (t.get("check_date") or t.get("survey:date") or e.get("timestamp") or "")[:4]
    r = {"n": name, "t": typ, "c": city, "s": state, "b": blurb, "lat": round(la, 5), "lon": round(lo, 5),
         "o": f"{e['type']}/{e['id']}"}
    if alt: r["a"] = alt
    if chain: r["br"] = chain[0]
    if addr: r["ad"] = addr
    if web: r["w"] = web
    if t.get("opening_hours"): r["h"] = t["opening_hours"][:80]
    if ig: r["ig"] = ig
    if fb: r["fb"] = fb
    if year.isdigit(): r["y"] = int(year)
    rows.append(r)


# ---------- merge curated ----------
def geocode(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 3, "countrycodes": "in"})
    req = urllib.request.Request(url, headers={"User-Agent": "india-bookstore-map/1.0 (personal project)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as f:
            return [(float(x["lat"]), float(x["lon"])) for x in json.load(f)]
    except Exception as ex:
        print("  geocode failed:", q, ex, file=sys.stderr)
        return []
    finally:
        time.sleep(1.1)


def link(r, name, on_osm):
    w, ig = LINKS.get(name, ("", ""))
    if w: r["w"] = w
    if ig: r["ig"] = ig
    if r.get("m"):
        return
    if name in UNCONFIRMED or (name in UNSEARCHED and name not in CONFIRMED_ANYWAY and not on_osm):
        r["u"] = 1
    else:
        r["v"] = 1


report = {"osm": 0, "geocoded": 0, "approx": 0}
for c in C:
    name, key, city, state, typ, la, lo, blurb = c[:8]
    is_place = len(c) > 8
    hit = None
    if key:
        cands = [(hav(la, lo, r["lat"], r["lon"]), r) for r in rows
                 if not r.get("f") and key in norm(r["n"]) and hav(la, lo, r["lat"], r["lon"]) < 2.5]
        if cands:
            hit = min(cands, key=lambda x: x[0])[1]
    if hit:
        hit.update({"n": name, "t": typ, "c": city, "s": state, "b": blurb, "f": 1})
        hit.pop("br", None)
        link(hit, name, True)
        report["osm"] += 1
        continue
    r = {"n": name, "t": typ, "c": city, "s": state, "b": blurb, "lat": la, "lon": lo, "f": 1}
    src = "approx"
    if not is_place and GEOCODE:
        base = re.sub(r",.*", "", name)
        for q in (f"{base}, {city}",):
            near = [g for g in geocode(q) if hav(la, lo, g[0], g[1]) < 4]
            if near:
                r["lat"], r["lon"] = round(near[0][0], 5), round(near[0][1], 5)
                src = "geocoded"
                break
    if src == "approx" and not is_place:
        r["x"] = 1
    if is_place:
        r["m"] = 1
    link(r, name, False)
    report[src] += 1
    print(f"  {src:9s} {name} ({city}){' UNCONFIRMED' if r.get('u') else ''}", file=sys.stderr)
    rows.append(r)

# ---------- second source: Overture Maps places ----------
def opt(flag):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None


GENERIC_WORDS = set("book books store stores stall stalls house centre center depot depo shop shoppe the and of co company "
                    "sons bros brothers pvt ltd booksellers bookseller bookstore bookshop bookstall agency new sri shri shree "
                    "stationery stationary stationers stationaries stationarys xerox general corner world point press".split())


def core(n):
    return [w for w in norm(n).split() if w not in GENERIC_WORDS and len(w) > 1]


def name_sim(a, b):
    ca, cb = core(a), core(b)
    if not ca or not cb:
        return 1.0 if norm(a) == norm(b) else 0.0
    sa, sb = set(ca), set(cb)
    small = sa if len(sa) <= len(sb) else sb
    if small <= (sa | sb) and (small <= sa and small <= sb) and max(len(w) for w in small) >= 4:
        return 0.92
    import difflib
    return difflib.SequenceMatcher(None, " ".join(sorted(ca)), " ".join(sorted(cb))).ratio()


ov_path = opt("--overture")
want_sites = set()
ov_stats = {"matched": 0, "web": 0, "ig": 0, "fb": 0}
if ov_path:
    PROVIDER = {"meta": "Meta", "Microsoft": "Microsoft", "Foursquare": "Foursquare", "AllThePlaces": "AllThePlaces"}
    og = {}
    for o in json.load(open(ov_path, encoding="utf-8")):
        og.setdefault((int(o["lat"] * 50), int(o["lon"] * 50)), []).append(o)
    for r in rows:
        if r.get("m"):
            continue
        reach = 3.0 if r.get("x") else 1.0
        span = 2 if r.get("x") else 1
        gx, gy = int(r["lat"] * 50), int(r["lon"] * 50)
        hits = []
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for o in og.get((gx + dx, gy + dy), []):
                    d = hav(r["lat"], r["lon"], o["lat"], o["lon"])
                    if d > reach or o["c"] < 0.3:  # Overture itself doubts places below 0.3
                        continue
                    sim = name_sim(r["n"], o["n"])
                    generic = not core(r["n"])
                    if len(set(core(r["n"])) & set(core(o["n"]))) <= 1 and d > 0.3 and not r.get("x"):
                        continue  # one shared word is not enough beyond 300 m
                    ok = (sim >= 0.8 and not generic) or (sim >= 0.62 and d <= 0.3 and not generic) or (generic and sim == 1.0 and d <= 0.1)
                    if ok:
                        hits.append((sim - d / 10, o))
        if not hits:
            continue
        hits.sort(key=lambda h: -h[0])
        best = hits[0][1]
        ov_stats["matched"] += 1
        if "--show-matches" in sys.argv and ov_stats["matched"] % 9 == 0:
            print(f"   match: {r['n']!r} ~ {best['n']!r} {hav(r['lat'], r['lon'], best['lat'], best['lon']):.2f}km conf {best['c']}", file=sys.stderr)
        r["od"] = sorted({PROVIDER.get(x, x) for h in hits[:3] for x in h[1]["d"]})
        r["oc"] = best["c"]
        for u in best["w"] + best["s"]:
            u = u.strip()
            if "instagram.com/" in u and not r.get("ig"):
                h = re.sub(r"^.*instagram\.com/", "", u).strip("/").split("/")[0].split("?")[0]
                if h:
                    r["ig"] = h; ov_stats["ig"] += 1
            elif "facebook.com/" in u and not r.get("fb"):
                r["fb"] = u; ov_stats["fb"] += 1
            elif u.startswith("http") and not r.get("w") and not re.search(r"facebook|instagram|twitter|youtube|google\.|justdial|wa\.me|linktr", u):
                site = SITES.get(u)
                if site is None:
                    want_sites.add(u)
                elif site["code"] not in ("000", "404", "410", "ERR", "500", "502", "503"):
                    r["w"] = u; ov_stats["web"] += 1
    print("overture:", ov_stats, "| sites still to check:", len(want_sites), file=sys.stderr)
    if opt("--want-sites"):
        open(opt("--want-sites"), "w").write("".join(f"x\t{u}\n" for u in sorted(want_sites)))

rows.sort(key=lambda r: (r["s"], r["c"], r["n"].lower()))
with open(out_path, "w", encoding="utf-8") as f:
    f.write("// Generated by build/build_data.py. Map data (c) OpenStreetMap contributors, ODbL.\n")
    f.write("window.BOOKSTORES = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n")
import collections
print(len(rows), "stores;", report, "| stationers de-listed:", delisted, file=sys.stderr)
print(collections.Counter(r["t"] for r in rows), file=sys.stderr)
print(collections.Counter(r["s"] for r in rows).most_common(40), file=sys.stderr)
