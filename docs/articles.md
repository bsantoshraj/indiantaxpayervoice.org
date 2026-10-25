# Articles: review, publish and unpublish

How to take an article from the drafts doc to the public site, and off it again,
either in WordPress (wp-admin on staging) or on the command line. Both routes go
through the same checks and the same approval; use whichever suits the moment.

- **Staging** (`staging.indiantaxpayervoice.org`, private) is where you review. Every
  article from the repository is there as a draft; publishing one *on staging* says
  "reviewed".
- **Production** (`indiantaxpayervoice.org`) gets an article only through the
  "Publish or unpublish article" workflow, after your approval, and only the exact
  text you published on staging.

Why it works this way, and the workflow's checks: [ci-cd.md](ci-cd.md#publish-an-article-controlled-release).

## One-time setup

| For | You need |
|---|---|
| wp-admin on staging | The Cloudflare email code (sent to the admin address) and the staging WordPress login: `ssh deploy@134.209.157.144 "grep -E '^WP_ADMIN_(USER\|PASSWORD)=' /opt/itv/.env"` in your own terminal |
| The command line | On the admin machine: the repository (`git pull` on `main`), `gh` signed in as the owner (`gh auth status`), and SSH as `deploy` to both droplets |

Articles are named by number (`11`) or by slug (the end of the article's address,
`no-tax-up-to-rs-12-lakh-…`). `scripts/article.sh` accepts either.

## The steps

| Step | In wp-admin (staging) | On the command line |
|---|---|---|
| **See where everything is** | Posts (the list shows Draft / Published) | `scripts/article.sh list` — every article, its status on staging and on production |
| **One article in detail** | — | `scripts/article.sh status 11` — both sites, whether each has the repository's text, and what to do next |
| **Review** | Posts › Drafts › open the article › **Preview** | `scripts/article.sh show 11` (the text) and `scripts/article.sh preview 11` (a staging preview link) |
| **Mark it reviewed: publish on staging** | In the editor, **Publish** | `scripts/article.sh stage 11` |
| **Publish to production** | Editor sidebar › **Production** › **Publish to production** (or hover the article in Posts) | `scripts/article.sh publish 11` |
| **Approve** | GitHub › Actions › the run › **Review deployments** › production › **Approve and deploy** | `scripts/article.sh approve` (the waiting run) or `scripts/article.sh approve <run-id>`; it asks before approving |
| **Confirm** | Open the article's address; it appears on the Research page | `scripts/article.sh watch` (follows the latest run and prints the result) |
| **Unpublish from production** | Production box › **Unpublish from production** | `scripts/article.sh unpublish 11`, then approve |
| **Take it off staging** | In the editor, switch to **Draft** and Update | `scripts/article.sh unstage 11` |

Unpublishing returns the article to draft on production: it is kept, not deleted,
and can be published again. It stays published on staging until you unstage it.

## A complete session on the command line

```console
$ git pull                                   # the latest articles
$ scripts/article.sh list
NN   staging    production  slug
...
11   draft      -           no-tax-up-to-rs-12-lakh-who-it-helps-who-pays-and-the-cliff-at-rs-12-7

$ scripts/article.sh show 11                 # read it (q to quit)
$ scripts/article.sh preview 11              # or look at it on staging in the browser
$ scripts/article.sh stage 11                # reviewed: published on staging
$ scripts/article.sh publish 11              # ask GitHub to publish it on production
Run 40195633452: https://github.com/…/actions/runs/40195633452
It waits for your approval: scripts/article.sh approve 40195633452
$ scripts/article.sh approve                 # shows the run, asks y/N, then follows it
staging: publish 61c7f27…; main: 61c7f27…
no-tax-up-to-rs-12-lakh-…: post 49, publish
https://indiantaxpayervoice.org/no-tax-up-to-rs-12-lakh-…/ -> 200
Run 40195633452 succeeded
```

Taking it down again is `scripts/article.sh unpublish 11`, then
`scripts/article.sh approve`; the run ends with the address answering 404.

## Correcting a published article

1. Edit the article in the drafts doc, export it and split it into
   `research/articles/` (`python3 -I research/scripts/split_articles.py <export>`),
   then open a PR and merge it.
2. The staging deploy puts the article **back to draft** on staging, because its text
   changed. `scripts/article.sh status 11` shows production now "differs from the
   repo".
3. Review it and `stage` it again, then `publish` and `approve`. Production's copy is
   updated in place (same address). Note the correction in the article itself, as the
   Research page promises.

## When something is refused

| Message | Meaning | What to do |
|---|---|---|
| `… is draft on staging: review it and run 'scripts/article.sh stage …' first` | Production only takes articles published on staging | Review, then `stage` |
| `staging shows different text from your repository` | Your checkout and staging differ: an unpulled merge, or a staging deploy still running | `git pull`, wait for the staging deploy (`gh run watch`), review again |
| The run fails at "Only what was reviewed and published on staging" | The same two checks, made by GitHub | As above |
| `no run is waiting for approval` | Nothing to approve, or it was already approved or cancelled | `gh run list -R bsantoshraj/indiantaxpayervoice.org --workflow publish-article.yml` |
| `… is not on staging yet` | The article is not merged, or the staging deploy has not run | Merge it and wait for the deploy |
| Unpublish says `not on this site` | It was never on production | Nothing to do; the run still checks the address answers 404 |

## Under the hood: WP-CLI

`scripts/article.sh` runs WP-CLI on the droplets over SSH, through
`research/scripts/wp_article.sh` (in `/opt/itv` on each droplet, and in the
repository locally):

```sh
ssh deploy@134.209.157.144          # staging (production: 64.227.176.80)
cd /opt/itv
research/scripts/wp_article.sh status <slug>       # "<status> <fingerprint>"
research/scripts/wp_article.sh publish <slug>      # publish the repository's text on this site
research/scripts/wp_article.sh unpublish <slug>    # back to draft on this site
research/scripts/wp_article.sh drafts              # every article as a draft (staging does this on each deploy)
research/scripts/wp_article.sh fingerprint <slug>  # fingerprint of the repository's text
```

Plain WP-CLI, for looking around (`docker compose run --rm -T wpcli wp …` in
`/opt/itv`, or in the repository for the local site):

```sh
wp post list --post_type=post --post_status=any --fields=ID,post_name,post_status
wp post get <id> --field=post_status
wp post meta get <id> _itv_source_sha256        # the text fingerprint the checks compare
```

**On production, change articles only through the workflow.** A `wp post update` or
`wp_article.sh publish` run directly on production skips your approval record and the
staging checks. On staging and on the local site, direct commands are fine.

The local site works the same way: `research/scripts/wp_article.sh drafts` loads every
article as a draft at `http://localhost:8080`, and `publish` / `unpublish` act on the
local site only.
