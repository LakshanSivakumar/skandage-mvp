FESTIVALS_2026 = {'Lunar New Year': '2026-02-17', 'Hari Raya Aidilfitri': '2026-03-20', 'Deepavali': '2026-11-08', 'Christmas': '2026-12-25', 'New Year': '2026-01-01', 'Mid-Autumn Festival': '2026-09-25', 'Hari Raya Haji': '2026-05-27', 'Pongal': '2026-01-14'}
def get_festival_date(festival_name, year=2026):
    return FESTIVALS_2026.get(festival_name)
def get_festivals_for_date(date_string):
    return [name for name, date in FESTIVALS_2026.items() if date == date_string]
