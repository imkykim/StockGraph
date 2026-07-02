class RelationTypes:
    SUPPLIES = "SUPPLIES"               # directed: supplier → customer
    CONTRACTS_WITH = "CONTRACTS_WITH"   # directed: buyer → supplier
    COMPETES_WITH = "COMPETES_WITH"     # symmetric
    CO_MENTION = "CO_MENTION"           # symmetric, use sparingly

SYMMETRIC_RELATIONS = {RelationTypes.COMPETES_WITH, RelationTypes.CO_MENTION}
DIRECTED_RELATIONS = {RelationTypes.SUPPLIES, RelationTypes.CONTRACTS_WITH}

# Relations that get folded into SUPPLIES (direction swap)
FOLD_TO_SUPPLIES = {"CUSTOMER_OF"}
