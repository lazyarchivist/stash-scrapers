# stash-scrapers

Scrapers for [Stash](https://github.com/stashapp/stash), published as a scraper
source that Stash installs and updates on its own.

| Scraper | Site | Scrapes | Works with |
|---|---|---|---|
| PimpBunny | pimpbunny.com | title, thumbnail, URL | Scrape by URL, Identify, Scene Tagger (from the scene's pimpbunny.com URL) |

## Using this source in Stash

1. Settings › Metadata Providers › **Available Scrapers** › **Add Source**.
2. Name it as you like, and use this URL:
   ```
   https://lazyarchivist.github.io/stash-scrapers/stable/index.yml
   ```
3. Install the scrapers you want from that source.

Stash then shows an update whenever a scraper changes here.

## How it is built

Each directory under `scrapers/` is one package. Its main file is `<id>.yml`;
any other file in the directory ships with it.

On every push to `main`, the GitHub Action runs `build.py`, which writes one zip
per scraper and an `index.yml` to `_site/stable/`, then publishes that to GitHub
Pages. A package's version is the hash of the last commit that touched its
directory, so Stash only flags the scrapers that actually changed.

To build locally:

```sh
pip install pyyaml
python build.py _site/stable
```

## Adding a scraper

1. Create `scrapers/<Id>/<Id>.yml` (the directory name is the package id).
2. Add any helper files alongside it.
3. If it depends on another package, declare it the CommunityScrapers way, with
   a `# requires: <id>` comment in the main file.
4. Push to `main`.
