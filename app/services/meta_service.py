from datetime import date

def get_ui_min_year() -> int:
    # TODO: später aus inventory ableiten
    return 1763

def get_ui_max_year() -> int:
    # aktuelles Vorjahr
    return date.today().year - 1