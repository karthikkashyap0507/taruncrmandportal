# Website checks (as a search engine sees it)

5 PASS, 0 FAIL.

| Item | Check | Result | Evidence |
|---|---|---|---|
| 1 | /jobs shows real jobs | PASS | the HTML sent for /jobs already lists the live job (visible without JavaScript) |
| 1b | Job pages are readable by search engines | PASS | job page has the job title in <title> and Google JobPosting data with monthly pay |
| 8 | robots.txt | PASS | 200 text/plain; allows public pages, blocks dashboards/API/sign-in, points to the sitemap |
| 9 | sitemap.xml | PASS | 200, valid XML, 8 URLs including the live job page /jobs/1, /privacy and /terms |
| 10 | Privacy Policy and Terms of Service | PASS | /privacy and /terms are separate pages (both 200, different content) and the footer links to each |
