from datetime import time

# Static drop times for each extension (in UTC) - To be used in the loader files and anywhere else it's needed.
DROP_TIMES = {
    'com': time(19, 0),
    'co': time(22, 0),
    'io': time(0, 30),
    'ai': time(22, 0),
}
