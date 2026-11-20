"""Diagnóstico temporal de Instagram (solo lectura, GET): datos de la cuenta y alcance de los
últimos Reels, para ver si Instagram los muestra a quien no te sigue. No publica nada."""
import os, json, requests
VER = os.environ.get("GRAPH_VERSION", "v23.0")
B = f"https://graph.facebook.com/{VER}"
TOK = os.environ["META_ACCESS_TOKEN"]
IG = os.environ["IG_USER_ID"]

def get(path, **params):
    params["access_token"] = TOK
    r = requests.get(f"{B}/{path}", params=params, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"texto": r.text[:300]}

st, cuenta = get(IG, fields="username,name,followers_count,follows_count,media_count,account_type")
print("CUENTA", st, json.dumps(cuenta, ensure_ascii=False))
st, lim = get(f"{IG}/content_publishing_limit", fields="config,quota_usage")
print("LIMITE", st, json.dumps(lim, ensure_ascii=False))
st, media = get(f"{IG}/media", fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", limit=15)
print("MEDIA", st, "n=", len(media.get("data", [])) if isinstance(media, dict) else media)
if st != 200:
    print(json.dumps(media, ensure_ascii=False)[:600])
for m in (media.get("data") or []):
    cap = (m.get("caption") or "").split("\n")[0][:60]
    res = {}
    for met in ("views", "reach", "saved", "shares", "total_interactions", "ig_reels_avg_watch_time"):
        s, ins = get(f"{m['id']}/insights", metric=met)
        if s == 200 and ins.get("data"):
            v = ins["data"][0].get("values", [{}])[0].get("value", ins["data"][0].get("total_value", {}).get("value"))
            res[met] = v
        else:
            res[met] = f"err{s}:{(ins.get('error') or {}).get('message','')[:70]}"
    print(m.get("timestamp", "")[:16], m.get("media_product_type"), "|", cap, "|",
          "likes", m.get("like_count"), "coment", m.get("comments_count"), "|", json.dumps(res, ensure_ascii=False))
st, ins = get(f"{IG}/insights", metric="reach,views,follower_count", period="day", metric_type="total_value")
print("CUENTA_INSIGHTS", st, json.dumps(ins, ensure_ascii=False)[:800])
