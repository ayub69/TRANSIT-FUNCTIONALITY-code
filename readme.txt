to run:

visual tests:
===========================================================
TRANSIT BACKEND TESTER — USAGE GUIDE
(For FR2.1.1, FR2.1.2, and FR2.1.3.a)
===========================================================

This tester is designed to validate the functionality of the TransitBackend
class according to the Functional Requirements (FR) defined in the SRS.

The tester is MENU DRIVEN and allows you to interactively verify how
the backend handles stop searches, nearest-stop detection, and routing.

-----------------------------------------------------------
OPTION 1 — SHOW ALL STOPS
FR Reference: Data Setup (Pre-FR2.1)
-----------------------------------------------------------
• Displays all 10 dummy stops and their coordinates.
• Helps the tester know which IDs (A–J) are available.

-----------------------------------------------------------
OPTION 2 — FR2.1.1
“Input Origin/Destination via Map Tap”
-----------------------------------------------------------
Simulates tapping on a map.

You manually enter:
    - latitude (dummy)
    - longitude (dummy)

Backend returns:
    • nearest stop ID
    • Euclidean distance (dummy units)

Validates:
    ✔ FR2.1.1.a (tap input)
    ✔ FR2.1.1.b (nearest stop identification)

-----------------------------------------------------------
OPTION 3 — FR2.1.2 (SIMPLE TEXT SEARCH)
“Search for stops using text”
-----------------------------------------------------------
You enter any text query such as:
    - "A"
    - "Stop"
    - "sto"
    - "C"
    - "xyz" (no match)

Backend returns:
    • List of stop IDs matching the query (case-insensitive)

Validates:
    ✔ FR2.1.2.a (search bar)
    ✔ FR2.1.2.b (partial matching allowed)

-----------------------------------------------------------
OPTION 4 — FR2.1.2 (ORIGIN + DESTINATION INPUT)
“Resolve origin and destination from text”
-----------------------------------------------------------
You enter text queries for BOTH:
    - origin
    - destination

Backend returns:
    • All matches for origin
    • All matches for destination
    • Automatically selects if there is EXACTLY ONE match

Validates:
    ✔ FR2.1.2.c (input origin and destination via text)
    ✔ FR2.1.2.d (backend resolves stop selection)
    ✔ FR2.1.2.e (supports multiple match scenarios)

Routing can only proceed when:
    origin_selected != None
    destination_selected != None

-----------------------------------------------------------
OPTION 5 — FR2.1.3.a
“Shortest Distance Route”
-----------------------------------------------------------
You enter:
    - Origin stop ID (A–J)
    - Destination stop ID (A–J)

Backend returns:
    • Path (list of stops)
    • Total graph distance (dummy units)

Validates:
    ✔ FR2.1.3.a (shortest distance optimization)
    ✔ Graph weight-based routing
    ✔ Proper error handling

-----------------------------------------------------------
OPTION 0 — EXIT
-----------------------------------------------------------

===========================================================
NOTES
===========================================================
• This tester ONLY covers FR2.1.1, FR2.1.2, and FR2.1.3.a.
• Later FRs (fastest route, cheapest route, transfers, etc.)
  will be added as backend functions are implemented.
• All coordinates are dummy values and do not represent real
  Karachi locations.
• All distances are Euclidean approximations used only for
  backend logic testing.
• This tester is SAFE, NON-GUI, and works fully in CLI.

===========================================================
END OF FILE
===========================================================
