# Darius Muglich's website

A small, buildless academic website. It uses plain HTML, CSS, and JavaScript,
system fonts, and a decorative canvas animation. No installation or build step
is needed. All essential content works without JavaScript.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Bio, publications, current research, and profile links |
| `style.css` | Typography, colours, responsive layout, and print styles |
| `animation.js` | Evolutionary ecology background and playback control |
| `favicon.svg` | Small branching icon for the browser tab |
| `cv.pdf` | Clearly labelled placeholder; replace with your academic CV |
| `CNAME` | Domain name: `dariusmuglich.com` |
| `.nojekyll` | Empty file for a plain static GitHub Pages site |
| `README.md` | Editing and upload instructions |

## Complete the content

Search `index.html` for `TODO:`. Before publishing:

1. Add your Google Scholar profile URL in the header and publication section.
2. Add your GitHub profile URL and email address.
3. Replace `cv.pdf` with your real CV, keeping the filename, and remove the
   placeholder `title` attribute from its link.
4. Confirm publication titles, complete author lists in publication order,
   venues, and years. Three entries have been seeded using previously discussed
   paper titles; the missing details are visibly bracketed. Author ordering must
   match each paper. Move the `<strong>Darius Muglich</strong>` element as needed.
5. Add each paper's PDF and code URLs; omit unavailable resources.
6. Replace the max-margin theory and neurosymbolic robotics blurbs. Review the
   discrete logic network blurb before publishing.

Unprovided links are inactive text rather than broken or guessed URLs.
To activate one, replace its entire `<span class="pending-link" ...>` with an
anchor. For example:

```html
<a href="YOUR_SCHOLAR_PROFILE_URL" target="_blank" rel="noopener">
  Scholar <span aria-hidden="true">↗</span>
</a>

<a href="YOUR_GITHUB_PROFILE_URL" target="_blank" rel="noopener">
  GitHub <span aria-hidden="true">↗</span>
</a>

<a href="mailto:YOUR_EMAIL_ADDRESS">
  Email <span aria-hidden="true">↗</span>
</a>
```

Use the same pattern for PDF, code, and the full Scholar list. Preserve
`class="section-link"` on the full-list anchor if you want its existing size.
Duplicate a complete `<li class="publication">` for another paper; remove
entries you do not want to include.

## Preview locally

Open `index.html` directly in your browser. Its relative CSS, JavaScript, SVG,
and PDF paths work from the same folder. For a local server, run this from the
folder containing `index.html`:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`. Stop the server with Ctrl+C.

## Upload to GitHub Pages

1. Create a public repository named **`YOUR_USERNAME.github.io`**, replacing
   `YOUR_USERNAME` with your actual GitHub username.
2. Extract this ZIP and upload the **contents of the website folder** to the
   repository root. `index.html` must be at the root, not inside an extra folder.
   Include `.nojekyll`; on macOS use Cmd+Shift+. in Finder to show it if needed.
3. Commit to `main`.
4. Open **Settings → Pages**. Under **Build and deployment**, select
   **Deploy from a branch**, then **main** and **/(root)**, and save.
5. Under **Custom domain**, enter `dariusmuglich.com` and save. The bundled
   `CNAME` contains that name; the file alone does not configure your domain.

If you want to test at `YOUR_USERNAME.github.io` first, omit `CNAME` and skip the
custom-domain setting until you are ready to connect the domain.

## Connect dariusmuglich.com

After adding the custom domain in GitHub's Pages settings, configure these DNS
records with your domain provider. Replace `YOUR_USERNAME` below.

| Type | Host/name | Value |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `YOUR_USERNAME.github.io` |

Replace any existing parking records for those same hosts; retain unrelated
email and verification records. Allow time for DNS to propagate, then enable
**Enforce HTTPS** in GitHub's Pages settings when it becomes available.

If you later change the domain, update `CNAME`, the canonical URL and
`og:url` in `index.html`, and the custom-domain setting in GitHub.

Official references, checked 12 October 2026:

- [Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Managing a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)

## Adjust the visual design

Edit the variables at the top of `style.css` for the palette and typefaces.
The ecology artwork is placed beside the bio on desktop and below it on
mobile. Its fade and position are controlled by `.ecology` and
`.hero-copy::before`.

The animation retains the supplied palette, branching, cursor repulsion, and
competition between organisms. It caps growth, batches canvas drawing, and
fades between generations. The animation can be paused; it starts as a still
image when the system requests reduced motion and stops drawing when the tab
is hidden or the bio is off screen. The decorative canvas cannot intercept
links or text selection.
