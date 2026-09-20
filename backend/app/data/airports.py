"""Major world airports dataset for autocomplete search.

Contains a curated list of major international airports with their
IATA code, name, city, and country. Used for the dropdown suggestion
feature when users type airport codes/names.
"""

AIRPORTS: list[dict] = [
    # --- India ---
    {"iata": "DEL", "name": "Indira Gandhi International Airport", "city": "New Delhi", "country": "India"},
    {"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj International Airport", "city": "Mumbai", "country": "India"},
    {"iata": "BLR", "name": "Kempegowda International Airport", "city": "Bengaluru", "country": "India"},
    {"iata": "MAA", "name": "Chennai International Airport", "city": "Chennai", "country": "India"},
    {"iata": "CCU", "name": "Netaji Subhas Chandra Bose International Airport", "city": "Kolkata", "country": "India"},
    {"iata": "HYD", "name": "Rajiv Gandhi International Airport", "city": "Hyderabad", "country": "India"},
    {"iata": "COK", "name": "Cochin International Airport", "city": "Kochi", "country": "India"},
    {"iata": "GOI", "name": "Dabolim Airport", "city": "Goa", "country": "India"},
    {"iata": "PNQ", "name": "Pune Airport", "city": "Pune", "country": "India"},
    {"iata": "AMD", "name": "Sardar Vallabhbhai Patel International Airport", "city": "Ahmedabad", "country": "India"},
    {"iata": "LKO", "name": "Chaudhary Charan Singh International Airport", "city": "Lucknow", "country": "India"},
    {"iata": "JAI", "name": "Jaipur International Airport", "city": "Jaipur", "country": "India"},
    {"iata": "BBI", "name": "Biju Patnaik International Airport", "city": "Bhubaneswar", "country": "India"},
    {"iata": "PAT", "name": "Jay Prakash Narayan Airport", "city": "Patna", "country": "India"},
    {"iata": "TRV", "name": "Trivandrum International Airport", "city": "Thiruvananthapuram", "country": "India"},
    {"iata": "IXC", "name": "Chandigarh International Airport", "city": "Chandigarh", "country": "India"},
    {"iata": "GAY", "name": "Gaya Airport", "city": "Gaya", "country": "India"},
    {"iata": "VNS", "name": "Lal Bahadur Shastri Airport", "city": "Varanasi", "country": "India"},
    {"iata": "IDR", "name": "Devi Ahilya Bai Holkar Airport", "city": "Indore", "country": "India"},
    {"iata": "NAG", "name": "Dr. Babasaheb Ambedkar International Airport", "city": "Nagpur", "country": "India"},
    {"iata": "SXR", "name": "Sheikh ul-Alam International Airport", "city": "Srinagar", "country": "India"},
    {"iata": "CCJ", "name": "Calicut International Airport", "city": "Kozhikode", "country": "India"},
    {"iata": "GAU", "name": "Lokpriya Gopinath Bordoloi International Airport", "city": "Guwahati", "country": "India"},
    {"iata": "VTZ", "name": "Visakhapatnam Airport", "city": "Visakhapatnam", "country": "India"},
    {"iata": "RAJ", "name": "Rajkot Airport", "city": "Rajkot", "country": "India"},
    {"iata": "DED", "name": "Dehradun Airport", "city": "Dehradun", "country": "India"},
    {"iata": "IMF", "name": "Imphal Airport", "city": "Imphal", "country": "India"},
    {"iata": "IXB", "name": "Bagdogra Airport", "city": "Bagdogra", "country": "India"},
    {"iata": "CJB", "name": "Coimbatore International Airport", "city": "Coimbatore", "country": "India"},
    {"iata": "MOH", "name": "Mohali International Airport", "city": "Mohali", "country": "India"},

    # --- United States ---
    {"iata": "JFK", "name": "John F. Kennedy International Airport", "city": "New York", "country": "USA"},
    {"iata": "LAX", "name": "Los Angeles International Airport", "city": "Los Angeles", "country": "USA"},
    {"iata": "ORD", "name": "O'Hare International Airport", "city": "Chicago", "country": "USA"},
    {"iata": "SFO", "name": "San Francisco International Airport", "city": "San Francisco", "country": "USA"},
    {"iata": "SEA", "name": "Seattle-Tacoma International Airport", "city": "Seattle", "country": "USA"},
    {"iata": "MIA", "name": "Miami International Airport", "city": "Miami", "country": "USA"},
    {"iata": "BOS", "name": "Boston Logan International Airport", "city": "Boston", "country": "USA"},
    {"iata": "DFW", "name": "Dallas/Fort Worth International Airport", "city": "Dallas", "country": "USA"},
    {"iata": "ATL", "name": "Hartsfield-Jackson Atlanta International Airport", "city": "Atlanta", "country": "USA"},
    {"iata": "DEN", "name": "Denver International Airport", "city": "Denver", "country": "USA"},
    {"iata": "LAS", "name": "Harry Reid International Airport", "city": "Las Vegas", "country": "USA"},
    {"iata": "PHX", "name": "Phoenix Sky Harbor International Airport", "city": "Phoenix", "country": "USA"},
    {"iata": "IAH", "name": "George Bush Intercontinental Airport", "city": "Houston", "country": "USA"},
    {"iata": "EWR", "name": "Newark Liberty International Airport", "city": "Newark", "country": "USA"},
    {"iata": "MSP", "name": "Minneapolis-Saint Paul International Airport", "city": "Minneapolis", "country": "USA"},
    {"iata": "DTW", "name": "Detroit Metropolitan Airport", "city": "Detroit", "country": "USA"},
    {"iata": "PHL", "name": "Philadelphia International Airport", "city": "Philadelphia", "country": "USA"},
    {"iata": "CLT", "name": "Charlotte Douglas International Airport", "city": "Charlotte", "country": "USA"},
    {"iata": "SAN", "name": "San Diego International Airport", "city": "San Diego", "country": "USA"},
    {"iata": "HNL", "name": "Daniel K. Inouye International Airport", "city": "Honolulu", "country": "USA"},
    {"iata": "DCA", "name": "Ronald Reagan Washington National Airport", "city": "Washington DC", "country": "USA"},
    {"iata": "IAD", "name": "Washington Dulles International Airport", "city": "Washington DC", "country": "USA"},

    # --- United Kingdom ---
    {"iata": "LHR", "name": "London Heathrow Airport", "city": "London", "country": "UK"},
    {"iata": "LGW", "name": "London Gatwick Airport", "city": "London", "country": "UK"},
    {"iata": "MAN", "name": "Manchester Airport", "city": "Manchester", "country": "UK"},
    {"iata": "EDI", "name": "Edinburgh Airport", "city": "Edinburgh", "country": "UK"},

    # --- Europe ---
    {"iata": "CDG", "name": "Charles de Gaulle Airport", "city": "Paris", "country": "France"},
    {"iata": "ORY", "name": "Orly Airport", "city": "Paris", "country": "France"},
    {"iata": "FRA", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "Germany"},
    {"iata": "MUC", "name": "Munich Airport", "city": "Munich", "country": "Germany"},
    {"iata": "AMS", "name": "Amsterdam Schiphol Airport", "city": "Amsterdam", "country": "Netherlands"},
    {"iata": "MAD", "name": "Adolfo Suárez Madrid-Barajas Airport", "city": "Madrid", "country": "Spain"},
    {"iata": "BCN", "name": "Barcelona-El Prat Airport", "city": "Barcelona", "country": "Spain"},
    {"iata": "FCO", "name": "Leonardo da Vinci-Fiumicino Airport", "city": "Rome", "country": "Italy"},
    {"iata": "MXP", "name": "Milan Malpensa Airport", "city": "Milan", "country": "Italy"},
    {"iata": "ZRH", "name": "Zurich Airport", "city": "Zurich", "country": "Switzerland"},
    {"iata": "GVA", "name": "Geneva Airport", "city": "Geneva", "country": "Switzerland"},
    {"iata": "VIE", "name": "Vienna International Airport", "city": "Vienna", "country": "Austria"},
    {"iata": "BRU", "name": "Brussels Airport", "city": "Brussels", "country": "Belgium"},
    {"iata": "CPH", "name": "Copenhagen Airport", "city": "Copenhagen", "country": "Denmark"},
    {"iata": "ARN", "name": "Stockholm Arlanda Airport", "city": "Stockholm", "country": "Sweden"},
    {"iata": "OSL", "name": "Oslo Gardermoen Airport", "city": "Oslo", "country": "Norway"},
    {"iata": "HEL", "name": "Helsinki Airport", "city": "Helsinki", "country": "Finland"},
    {"iata": "DUB", "name": "Dublin Airport", "city": "Dublin", "country": "Ireland"},
    {"iata": "LIS", "name": "Lisbon Airport", "city": "Lisbon", "country": "Portugal"},
    {"iata": "ATH", "name": "Athens International Airport", "city": "Athens", "country": "Greece"},
    {"iata": "IST", "name": "Istanbul Airport", "city": "Istanbul", "country": "Turkey"},

    # --- Middle East & Asia ---
    {"iata": "DXB", "name": "Dubai International Airport", "city": "Dubai", "country": "UAE"},
    {"iata": "AUH", "name": "Abu Dhabi International Airport", "city": "Abu Dhabi", "country": "UAE"},
    {"iata": "DOH", "name": "Hamad International Airport", "city": "Doha", "country": "Qatar"},
    {"iata": "RUH", "name": "King Khalid International Airport", "city": "Riyadh", "country": "Saudi Arabia"},
    {"iata": "JED", "name": "King Abdulaziz International Airport", "city": "Jeddah", "country": "Saudi Arabia"},
    {"iata": "KWI", "name": "Kuwait International Airport", "city": "Kuwait City", "country": "Kuwait"},
    {"iata": "SIN", "name": "Singapore Changi Airport", "city": "Singapore", "country": "Singapore"},
    {"iata": "BKK", "name": "Suvarnabhumi Airport", "city": "Bangkok", "country": "Thailand"},
    {"iata": "HKG", "name": "Hong Kong International Airport", "city": "Hong Kong", "country": "China"},
    {"iata": "NRT", "name": "Narita International Airport", "city": "Tokyo", "country": "Japan"},
    {"iata": "HND", "name": "Haneda Airport", "city": "Tokyo", "country": "Japan"},
    {"iata": "KIX", "name": "Kansai International Airport", "city": "Osaka", "country": "Japan"},
    {"iata": "ICN", "name": "Incheon International Airport", "city": "Seoul", "country": "South Korea"},
    {"iata": "PVG", "name": "Shanghai Pudong International Airport", "city": "Shanghai", "country": "China"},
    {"iata": "PEK", "name": "Beijing Capital International Airport", "city": "Beijing", "country": "China"},
    {"iata": "KUL", "name": "Kuala Lumpur International Airport", "city": "Kuala Lumpur", "country": "Malaysia"},
    {"iata": "CGK", "name": "Soekarno-Hatta International Airport", "city": "Jakarta", "country": "Indonesia"},
    {"iata": "MNL", "name": "Ninoy Aquino International Airport", "city": "Manila", "country": "Philippines"},
    {"iata": "CMB", "name": "Bandaranaike International Airport", "city": "Colombo", "country": "Sri Lanka"},
    {"iata": "KTM", "name": "Tribhuvan International Airport", "city": "Kathmandu", "country": "Nepal"},
    {"iata": "DAC", "name": "Hazrat Shahjalal International Airport", "city": "Dhaka", "country": "Bangladesh"},
    {"iata": "KHI", "name": "Jinnah International Airport", "city": "Karachi", "country": "Pakistan"},
    {"iata": "LHE", "name": "Allama Iqbal International Airport", "city": "Lahore", "country": "Pakistan"},
    {"iata": "ISB", "name": "Islamabad International Airport", "city": "Islamabad", "country": "Pakistan"},
    {"iata": "DMM", "name": "King Fahd International Airport", "city": "Dammam", "country": "Saudi Arabia"},
    {"iata": "BHR", "name": "Bahrain International Airport", "city": "Manama", "country": "Bahrain"},
    {"iata": "MCT", "name": "Muscat International Airport", "city": "Muscat", "country": "Oman"},

    # --- Australia / Oceania ---
    {"iata": "SYD", "name": "Sydney Kingsford Smith Airport", "city": "Sydney", "country": "Australia"},
    {"iata": "MEL", "name": "Melbourne Airport", "city": "Melbourne", "country": "Australia"},
    {"iata": "BNE", "name": "Brisbane Airport", "city": "Brisbane", "country": "Australia"},
    {"iata": "PER", "name": "Perth Airport", "city": "Perth", "country": "Australia"},
    {"iata": "AKL", "name": "Auckland Airport", "city": "Auckland", "country": "New Zealand"},
    {"iata": "WLG", "name": "Wellington International Airport", "city": "Wellington", "country": "New Zealand"},

    # --- Africa ---
    {"iata": "JNB", "name": "O.R. Tambo International Airport", "city": "Johannesburg", "country": "South Africa"},
    {"iata": "CPT", "name": "Cape Town International Airport", "city": "Cape Town", "country": "South Africa"},
    {"iata": "CAI", "name": "Cairo International Airport", "city": "Cairo", "country": "Egypt"},
    {"iata": "NBO", "name": "Jomo Kenyatta International Airport", "city": "Nairobi", "country": "Kenya"},
    {"iata": "LOS", "name": "Murtala Muhammed International Airport", "city": "Lagos", "country": "Nigeria"},

    # --- Canada ---
    {"iata": "YYZ", "name": "Toronto Pearson International Airport", "city": "Toronto", "country": "Canada"},
    {"iata": "YVR", "name": "Vancouver International Airport", "city": "Vancouver", "country": "Canada"},
    {"iata": "YUL", "name": "Montréal-Trudeau International Airport", "city": "Montreal", "country": "Canada"},
]


def search_airports(query: str, limit: int = 10) -> list[dict]:
    """Search airports by IATA code, name, city, or country.

    Performs a case-insensitive substring match against the IATA code,
    airport name, city name, and country. Returns up to ``limit`` matches.
    """
    q = query.strip().lower()
    if not q:
        return []

    matches: list[tuple[int, dict]] = []
    for airport in AIRPORTS:
        # Exact IATA code match gets highest priority
        if airport["iata"].lower() == q:
            matches.append((0, airport))
            continue

        # IATA code prefix
        if airport["iata"].lower().startswith(q):
            matches.append((1, airport))
            continue

        # Name contains query
        if q in airport["name"].lower():
            matches.append((2, airport))
            continue

        # City contains query
        if q in airport["city"].lower():
            matches.append((3, airport))
            continue

        # Country contains query
        if q in airport["country"].lower():
            matches.append((4, airport))

    # Sort by priority then by IATA code
    matches.sort(key=lambda item: (item[0], item[1]["iata"]))
    return [airport for _, airport in matches[:limit]]