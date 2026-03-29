import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE = "https://openlibrary.org"
HEADERS = {"User-Agent": "BookExplorer/1.0 (learning project)"}


def fetch(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "no internet connection"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search/books")
def search_books():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "query required"}), 400

    data = fetch(f"{BASE}/search.json", {
        "q": q,
        "limit": 10,
        "fields": "key,title,author_name,first_publish_year,number_of_pages_median,subject,cover_i"
    })

    if "error" in data:
        return jsonify(data), 502

    books = []
    for doc in data.get("docs", []):
        books.append({
            "key":     doc.get("key", ""),
            "title":   doc.get("title", "Unknown title"),
            "authors": doc.get("author_name", []),
            "year":    doc.get("first_publish_year"),
            "pages":   doc.get("number_of_pages_median"),
            "subjects": doc.get("subject", [])[:6],
            "cover_id": doc.get("cover_i"),
        })

    return jsonify({"results": books, "total": data.get("numFound", 0)})


@app.route("/api/search/authors")
def search_authors():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "query required"}), 400

    data = fetch(f"{BASE}/search/authors.json", {"q": q, "limit": 8})

    if "error" in data:
        return jsonify(data), 502

    authors = []
    for a in data.get("docs", []):
        authors.append({
            "key":        a.get("key", ""),
            "name":       a.get("name", "Unknown"),
            "birth_date": a.get("birth_date", ""),
            "death_date": a.get("death_date", ""),
            "top_work":   a.get("top_work", ""),
            "work_count": a.get("work_count", 0),
        })

    return jsonify({"results": authors})


@app.route("/api/search/subject")
def search_subject():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "query required"}), 400

    slug = q.lower().replace(" ", "_")
    data = fetch(f"{BASE}/subjects/{slug}.json", {"limit": 10})

    if "error" in data:
        return jsonify(data), 502

    works = []
    for w in data.get("works", []):
        works.append({
            "key":     w.get("key", ""),
            "title":   w.get("title", ""),
            "authors": [a["name"] for a in w.get("authors", [])],
            "cover_id": w.get("cover_id"),
        })

    return jsonify({
        "name":       data.get("name", q),
        "work_count": data.get("work_count", 0),
        "results":    works,
    })


@app.route("/api/book/<path:work_id>")
def book_detail(work_id):
    data = fetch(f"{BASE}/works/{work_id}.json")
    if "error" in data:
        return jsonify(data), 502

    desc = data.get("description", "")
    if isinstance(desc, dict):
        desc = desc.get("value", "")

    return jsonify({
        "title":       data.get("title", ""),
        "description": desc[:800] if desc else "",
        "subjects":    data.get("subjects", [])[:8],
        "links":       [{"title": l.get("title", ""), "url": l.get("url", "")}
                        for l in data.get("links", [])[:3]],
    })


@app.route("/api/author/<author_id>")
def author_detail(author_id):
    data = fetch(f"{BASE}/authors/{author_id}.json")
    if "error" in data:
        return jsonify(data), 502

    bio = data.get("bio", "")
    if isinstance(bio, dict):
        bio = bio.get("value", "")

    works_data = fetch(f"{BASE}/authors/{author_id}/works.json", {"limit": 6})
    works = []
    for w in works_data.get("entries", []):
        works.append({
            "title": w.get("title", ""),
            "year":  w.get("first_publish_date", ""),
        })

    return jsonify({
        "name":       data.get("name", ""),
        "bio":        bio[:700] if bio else "",
        "birth_date": data.get("birth_date", ""),
        "death_date": data.get("death_date", ""),
        "works":      works,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
