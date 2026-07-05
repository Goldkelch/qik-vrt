# QIKVRT ODU V1.5 Zenodo GitHub Upload and Publish

Status: `V1_5_ZENODO_GITHUB_AUTH_PUBLISH_VARIANT`

Purpose: publish `assets/pdf/odu_proof.pdf` as the Zenodo PDF artifact while binding the owner-side identity to the Zenodo account that the owner created or accessed through GitHub login.

Important distinction:

- Zenodo can be logged into through GitHub in the web UI.
- The Zenodo REST API does not accept a GitHub token as a Zenodo upload token.
- The script therefore uses a `ZENODO_ACCESS_TOKEN` generated in the Zenodo account that has been authenticated via GitHub.
- The script uses `GITHUB_USERNAME` for declared creator identity and can validate control of that GitHub account if `GITHUB_TOKEN` is also supplied.
- The script does not write tokens to disk.

Owner-side expected workflow:

1. Log in to Zenodo with the GitHub account in the browser.
2. Generate a Zenodo personal access token with deposit write permission.
3. In Windows, set environment variables:
   - `set ZENODO_ACCESS_TOKEN=...`
   - `set GITHUB_USERNAME=Goldkelch` or the correct owner GitHub username.
   - optional: `set GITHUB_REPO_URL=https://github.com/Goldkelch/qik-vrt`
   - optional: `set GITHUB_TOKEN=...` for GitHub token owner verification.
4. Run `DRY_RUN_VERIFY_ONLY.cmd`.
5. Run `ZENODO_UPLOAD_AND_PUBLISH.cmd`.
6. Type exactly `PUBLISH QIKVRT` when the script prints the final publication check.

Safety and QIK-VRT status:

- PDF SHA256 is verified before upload: `2382b5d4970559bc28649a6deb6797fe867fc70439140e4cf1c1e59964a37de6`.
- Publication does not proceed without typed confirmation.
- No local deletion or cleanup command is present in the upload scripts.
- Result JSON is written to `zenodo/zenodo_publish_result.json`.

