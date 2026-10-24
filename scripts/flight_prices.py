"""Associate returned one-leg Google offers with exact flights, in a verified currency."""
from decimal import Decimal,InvalidOperation
import json
import re


def verify_fare_context(body, currency):
    if not re.search(r'Currency\s*'+re.escape(currency)+r'\b',body) or not re.search(r'One way\s+1\s+Economy\b',body):
        raise ValueError('Unverified currency or one-adult economy fare context')


def cheapest_prices(scripts, flights, currency):
    known={f['id']:f for f in flights};quotes={}
    def walk(value):
        if not isinstance(value,list):return
        # An offer row contains one itinerary and its own price. Never take a
        # page minimum or assign a connecting itinerary total to one segment.
        if len(value)>1 and isinstance(value[0],list) and len(value[0])>12:
            itinerary=value[0]
            legs=itinerary[2]
            if isinstance(legs,list) and len(legs)==1 and isinstance(legs[0],list):
                leg=legs[0]
                if len(leg)>22 and isinstance(leg[20],list) and len(leg[20])==3 and isinstance(leg[22],list) and len(leg[22])>=2:
                    try:
                        day='-'.join(f'{v:02}' if i else str(v) for i,v in enumerate(leg[20]))
                        identity=f"{day}:{leg[22][0]}{leg[22][1]}:{leg[3]}:{leg[6]}"
                        amount=value[1][0][1]
                        if identity in known and not isinstance(amount,bool) and isinstance(amount,(int,float)):
                            number=Decimal(str(amount))*100
                            if number.is_finite() and number>0 and number==number.to_integral_value():
                                quotes.setdefault(identity,[]).append(int(number))
                    except (IndexError,TypeError,ValueError,InvalidOperation):pass
        for child in value:walk(child)
    for script in scripts:
        match=re.search(r"AF_initDataCallback\(\{key:.*?data:",script)
        if match:
            try:data,_=json.JSONDecoder().raw_decode(script[match.end():])
            except ValueError:continue
            walk(data)
    return {identity:dict(amount_minor=min(values),currency=currency,adults=1,cabin='economy',trip_type='one_way',basis='lowest_returned_quote') for identity,values in quotes.items()}
