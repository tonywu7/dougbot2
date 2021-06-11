def merge_collections(*mappings):
    base = {}
    base.update(mappings[0])
    for m in mappings[1:]:
        for k, v in m.items():
            if k in base and type(base[k]) is type(v):
                if isinstance(v, dict):
                    base[k] = merge_collections(base[k], v)
                elif isinstance(v, set):
                    base[k] |= v
                elif isinstance(v, list):
                    base[k].extend(v)
                else:
                    base[k] = v
            else:
                base[k] = v
    return base
