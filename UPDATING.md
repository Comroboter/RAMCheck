# How to publish an update

The version number lives in one place: `VERSION = "..."` near the top of `core.py`. The installer, the exe properties and the Store package all take it from there.

## 1. Change the code

Edit the files, or replace them with new ones. Then:

1. Raise `VERSION` in `core.py` (for example `1.1` to `1.2`)
2. Add a section for the new version at the top of `CHANGELOG.md`

## 2. Upload to GitHub

1. Open the repository > **Add file** > **Upload files**
2. Drag in all changed files and folders. Files with the same name are replaced
3. Files that no longer exist must be deleted by hand: open the file > **...** (top right) > **Delete file**
4. Commit message, for example `RAMCheck 1.2`, then **Commit changes**

## 3. Publish the release

1. **Releases** > **Draft a new release**
2. **Choose a tag** > type `v1.2` (same number as in `core.py`) > **Create new tag**
3. Title `RAMCheck 1.2`, description: copy the new part of `CHANGELOG.md`
4. **Publish release**, without attaching any files

GitHub Actions now builds the installer, the portable exe, the terminal version and the checksums and attaches them to the release. That takes about 5 to 10 minutes. Follow it in the **Actions** tab. A green check means done, a red X means something failed: click it to see the log.

Everyone running an older version sees "RAMCheck 1.2 is available" in the app.

## 4. Microsoft Store

Once the Store variables are set up (see `packaging/store/STORE_GUIDE.md`), the same workflow run also builds `RAMCheck-Store.msix`. Download it from the run's **Artifacts**, then in Partner Center: your app > **Update** > **Packages** > upload it > **Submit**.
