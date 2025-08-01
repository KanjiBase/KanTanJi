from utils_data_entitites import Entry, Value

ADJECTIVE_TYPE_COLOR = "#ACA52F"
VERB_TRANSITIVENESS_COLOR = "#28835F"
VERB_IGIDAN_GODAN_COLOR = "#658B18"
VERB_SURU_COLOR = "#4A90E2"
VERB_IRREGULAR_COLOR = "#E65563"

def get_smart_label(title: str, details: str, color="#d73a49"):
    return f"""
<span class="property-label" onclick="this.querySelector('span').style.display = (this.querySelector('span').style.display === 'none' || this.querySelector('span').style.display === '') ? 'block' : 'none';" style="display: inline-block; background-color: {color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; font-family: Arial, sans-serif; cursor: pointer; position: relative; margin-right: 8px;">
    {title}
    <span style="display: none; position: absolute; top: 120%; left: 0; background-color: white; color: black; border: 1px solid {color}; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-family: Arial, sans-serif; z-index: 10; min-width: 150px;">
        {details}
    </span>
</span>    
"""


def get_reading_html(text):
    reading = str(text).split('・')
    if len(reading) == 2:
        return f'<span style="font-weight: bold">{reading[0]}<span style="color: gray;">・{reading[1]}</span></span>'
    if len(reading) != 1:
        print('E: reading with multiple separators!', text)
    return f'<span style="font-weight: bold">{text}</span>'


def get_unimportant_reading_html(text):
    return f'<span style="color: gray;">{text}</span>'


def vocab_property_html(prop: str | Value, color: str):
    match str(prop):
        case "ichidan":
            return get_smart_label("ichidan (..る)", "Sloveso má pouze jeden tvar, při skloňování většinou odpadá ~る přípona.", color)
        case "godan":
            return get_smart_label("godan (..う)", "Sloveso má pět tvarů jako je pět samohlásek, pro skloňování mají dle typu koncovky různá pravidla.", color)
        case "jidoushi":
            return get_smart_label("netranzitivní", "neboli 'じどうし', sloveso popisuje podmět (budova se staví)", color)
        case "tadoushi":
            return get_smart_label("tranzitivní", "neboli 'たどうし', sloveso může popisovat předmět (postavili budovu)", color)
        case "i":
            return get_smart_label("い - příd. jméno", "Koncovka ~い buď zůstává, nebo se nahrazuje např. v záporu za ~くない.", color)
        case "na":
            return get_smart_label("な - příd. jméno", "Většinou koncovka ~な odpadá (např. při použití s 'です'), pokud se neváže na podstatné jméno.", color)
        case "suru":
            return get_smart_label("する sloveso","Nepravidelná slovesa se chovají podobně dle する tvaru.", color)
        case "fukisokuna":
            return get_smart_label("nepravidelné čtení","Čtení nelze odvodit ze zápisu kanji.", color)
    raise ValueError(f"Property not allowed: {prop}")


def vocab_property_color(prop: str | Value):
    match str(prop):
        case "ichidan" | "godan":
            return VERB_IGIDAN_GODAN_COLOR
        case "jidoushi" | "tadoushi":
            return VERB_TRANSITIVENESS_COLOR
        case "i" | "na":
            return ADJECTIVE_TYPE_COLOR
        case "suru":
            return VERB_SURU_COLOR
        case "fukisokuna":
            return VERB_IRREGULAR_COLOR
    raise ValueError(f"Property not allowed: {prop}")


def parse_item_props_html(word: Entry):
    props = word["raberu"]
    return "".join(map(lambda x: vocab_property_html(x, vocab_property_color(x)), props))
