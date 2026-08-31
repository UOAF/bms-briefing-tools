# UOAF Community Event Publishing

Use this workflow only when the user explicitly asks to prepare or publish the
community-facing event. It performs external writes to Google Drive and Sheets.
It does not authorize a Claude/design handoff, repository commit, push, or the
actual sending of the Discord message.

## 1. Prepare The Publish Plan

Run the deterministic local helper after the root player brief and requested
package syntheses are current:

```powershell
python .\scripts\prepare_bms_community_publish.py `
  --campaign-dir "<BMS theater campaign folder>" `
  --prefix "<prefix>" `
  --output-dir ".\outputs\<prefix>\community_publish" `
  --synthesis ".\outputs\<prefix>\briefing_synthesis.json" `
  --synthesis ".\outputs\<prefix>\pkg<second-id>\briefing_synthesis.json" `
  --package-id <primary-id> --package-id <second-id> `
  --event-number <event-number> `
  --operation-name "<operation name>" `
  --event-date YYYY-MM-DD `
  --briefing-time 1800 --marshal-time 1745 `
  --theater "<theater>" --bms-version "4.38.1" `
  --mission-objectives "<concise player-facing objective summary>" `
  --event-folder-url "<event Drive folder URL>" `
  --briefing-url "<current briefing URL>"
```

The helper is intentionally network-free. It writes:

- `community_publish_plan.json`: checksummed upload inventory, INI identity,
  package/flight/seat rows, event metadata, and the completion contract.
- `discord_post.txt`: a post with a calculated Discord timestamp. Until the
  final signup URL exists, it contains `<SIGNUP_SHEET_URL>` and is not ready.

Inventory only files directly inside the supplied campaign directory whose
name is exactly the prefix or begins with `<prefix>.`. Include all matching
sidecars and backups returned by the plan. Do not sweep other folders or upload
similarly named project context files.

## 2. Upload Mission Files

Locate the current numeric event folder under the user-provided events root.
Upload every entry in `mission_files`. On a rerun, update or replace a file with
the same name rather than creating duplicates. Re-read the event folder and
compare the final name set to the plan. The current `<prefix>.ini` is the file
that must be linked from the signup sheet.

Never report an upload count based only on attempted calls. Report the verified
count and name any failed or extra duplicate files.

## 3. Copy And Adapt The Signup Sheet

Find the latest prior numeric event that has a native Google signup Sheet and
copy that Sheet into the current event folder. Do not edit the prior event's
sheet. Preserve all tabs, formulas, formatting, merged cells, data validation,
checkboxes, and protected controls unless the current template requires a
specific change.

Inspect the copied workbook before writing. Use the template's actual roles and
ranges rather than assuming fixed coordinates. Populate:

- Current event number and operation name.
- One block per current player package.
- Flight callsign, role/task, aircraft type, and available seat count from the
  publish plan.
- Current theater.
- Current briefing link.
- A link to the uploaded current-event INI file.

For the Event 739-744 template family, package blocks commonly begin at rows 4,
13, and 22; theater/briefing/INI commonly live near `K36`, `K38`, and `K40`.
These are discovery hints, not universal write coordinates. Inspect first.

Blank every prior pilot-name or pilot-assignment entry in the copied sheet and
reset signup checkboxes to false. Clear values only; preserve formatting,
validation, formulas, and protected/template cells. If a package block is
unused, label it clearly as not tasked and remove stale flight choices from the
signup dropdown source.

Verify the workbook after writing:

- Package and flight rows exactly match the publish plan.
- Pilot cells are blank and checkboxes are reset.
- Flight-choice validation contains current callsigns only.
- Formula/helper tabs contain no `#REF!`, `#N/A`, or stale prior-event flight
  names.
- Briefing and INI hyperlinks open the intended current-event resources.

## 4. Set And Verify Sharing

The signup sheet must allow anyone with the link to edit. Use a Drive connector
when it supports an `anyone` permission with role `writer`. If the connector
cannot create public link permissions, use the signed-in browser UI, confirm the
action at the point the UI changes access, and then re-read sharing metadata.

Do not infer success from the sharing dialog or from a previously public
template. Report public editing only after the copied sheet itself is verified
as `type=anyone`, `role=writer`. If authentication or confirmation blocks the
change, return the completed sheet and state that permission verification is
still outstanding.

## 5. Finalize The Discord Post

Rerun the helper with `--signup-url` set to the copied Sheet's final URL. Use a
short objective paragraph grounded in the current root player brief and planner
intent. Never copy tactical text, dates, or Unix timestamps from a prior event.

The output format is:

```text
@BMS Events
You are invited to UOAF BMS Event #<event>!
**<operation>**

When: <weekday>, <day> <month> <year>, <t:<calculated-unix-time>:t>
Theater: <theater>
Version: BMS <version>

Mission objectives:
<concise player-facing summary>

Marshal: <HHMM>z. Briefing: <HHMM>z.

ALL INFORMATION (including Discord link, Briefing, INI file, and Theater) is available at the bottom of the RSVP link:
<signup URL>
```

Return the post ready to paste, but do not send it unless the user explicitly
asks to post it to Discord and a Discord tool is available.

## 6. Create The Event Banner

Generate a wide, Discord-friendly event banner grounded in the operation name
and mission character. Read and apply
[event-banner-criteria.md](event-banner-criteria.md). Use the canonical UOAF roundel at
`assets/uoaf-roundel.png` as an image reference. Preserve the logo's identity,
wording, compass/aircraft motif, proportions, and colors; do not let image
generation reinterpret it or add unrelated unit markings.

Keep the event number and operation title readable at Discord preview size.
Save the final banner under:

`outputs/<prefix>/community_publish/event-<number>-<slug>-banner.png`

Inspect the final image. Verify exact title spelling, logo fidelity, no extra
text, no malformed aircraft, and sufficient contrast. Return a preview or
clickable file link. Upload the banner to the event folder only when the user
asked for the event package to be uploaded or published.

## 7. Completion Report

Return all of the following together:

- Event-folder link.
- Signup-sheet link.
- Verified mission-file upload count, including the INI filename.
- Verified signup-sheet sharing state, or a precise outstanding blocker.
- The complete Discord-ready post in a code block.
- The banner preview/link.

Do not claim the entire publish workflow is complete if any completion-contract
item in `community_publish_plan.json` remains unverified.
