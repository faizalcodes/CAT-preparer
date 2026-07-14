# CAT Prep Reader

## Setup
```
pip install -r requirements.txt
```

## Add an article
```
export FIRECRAWL_API_KEY=your_key
export OPENROUTER_API_KEY=your_key
python generate_article.py "https://example.com/some-article" --category psychology-philosophy --part 3
```
This drops a new `articles/<category>/part-<n>.md` file. Parts within a category unlock in order (part 2 unlocks once part 1 is marked complete).

## Run the app
```
python app.py
```
Then open http://localhost:5000, pick Shobhana (lavender) or Faiz (ocean), and start reading.

## Notes
- Streak counts consecutive days with at least one completed article.
- Click any highlighted word in the article, or any word in the sidebar Word Bank, to see its meaning + example.
- To add more categories, just make a new folder under `articles/` and drop `part-1.md`, `part-2.md`, etc. in it.

python generate_article.py "https://aeon.co/essays/when-my-ties-to-my-mother-faded-so-did-my-memories" --category "psychology-philosophy" --part 1