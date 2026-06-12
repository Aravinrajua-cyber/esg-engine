# Frontend Build Blocker

## Summary

The frontend build has not been verified. The current environment prevents npm from installing the Vite/React/TypeScript dependencies required by `site/package.json`.

## Diagnostic Commands Run

```bat
cd /d C:\Hackathon\esg-engine\site
node --version
npm.cmd --version
npm.cmd config get registry
npm.cmd config get cache
npm.cmd config get prefix
npm.cmd config get proxy
npm.cmd config get https-proxy
npm.cmd config get strict-ssl
npm.cmd cache verify
npm.cmd install --cache .npm-cache --prefer-offline --verbose --fetch-retries=0 --fetch-timeout=30000
npm.cmd ping --cache .npm-cache --fetch-retries=0 --fetch-timeout=30000 --verbose
```

## Observed Outputs

```text
node --version
v24.14.1

npm.cmd --version
11.11.0

npm.cmd config get registry
https://registry.npmjs.org/

npm.cmd config get cache
C:\Users\aravi\AppData\Local\npm-cache

npm.cmd config get prefix
C:\Users\aravi\AppData\Roaming\npm

npm.cmd config get proxy
null

npm.cmd config get https-proxy
null

npm.cmd config get strict-ssl
true
```

`npm.cmd cache verify` failed against the default cache:

```text
npm error code EPERM
npm error syscall unlink
npm error path C:\Users\aravi\AppData\Local\npm-cache\_cacache\content-v2\sha512\...
npm error The operation was rejected by your operating system.
npm error Log files were not written due to an error writing to the directory: C:\Users\aravi\AppData\Local\npm-cache\_logs
```

The project-local cache could write logs, but package fetching still failed:

```text
npm.cmd install --cache .npm-cache --prefer-offline --verbose --fetch-retries=0 --fetch-timeout=30000

npm http fetch GET https://registry.npmjs.org/@vitejs%2fplugin-react attempt 1 failed with EACCES
npm http fetch GET https://registry.npmjs.org/vite attempt 1 failed with EACCES
npm http fetch GET https://registry.npmjs.org/typescript attempt 1 failed with EACCES
npm http fetch GET https://registry.npmjs.org/react attempt 1 failed with EACCES
npm http fetch GET https://registry.npmjs.org/react-dom attempt 1 failed with EACCES
npm http fetch GET https://registry.npmjs.org/plotly.js-dist-min attempt 1 failed with EACCES
npm http fetch GET https://registry.npmjs.org/lucide-react attempt 1 failed with EACCES
npm error code EACCES
npm error FetchError: request to https://registry.npmjs.org/@vitejs%2fplugin-react failed
```

`npm.cmd ping --cache .npm-cache --fetch-retries=0 --fetch-timeout=30000 --verbose` also failed:

```text
npm notice PING https://registry.npmjs.org/
npm http fetch GET https://registry.npmjs.org/-/ping attempt 1 failed with EACCES
npm error code EACCES
npm error FetchError: request to https://registry.npmjs.org/-/ping failed
```

## Likely Cause

There are two separate limitations:

1. The default npm cache under `C:\Users\aravi\AppData\Local\npm-cache` is not usable by npm in this session. `npm cache verify` fails with `EPERM unlink`, and npm cannot write normal debug logs there. This may be Windows file locking, antivirus/controlled-folder access, or permissions on that cache directory.
2. Package fetching itself is blocked in the current execution environment. A workspace-local cache under `C:\Hackathon\esg-engine\site\.npm-cache` can write logs, but npm still receives `EACCES` on HTTPS requests to `registry.npmjs.org`. Registry and proxy settings are normal (`registry=https://registry.npmjs.org/`, `proxy=null`, `https-proxy=null`), so this is most consistent with restricted outbound network access or the current execution sandbox.

This does not look like an unwritable global prefix problem: no global install was attempted for the project, and the failure occurs before dependency extraction into `node_modules`.

## Commands To Run Later In A Normal Terminal

Run these from a regular user terminal with outbound network access:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

If the default npm cache remains locked on the local machine, use a project-local cache:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install --cache .npm-cache
npm.cmd run build
npm.cmd run dev
```

## Build Verification Once Dependencies Are Available

The frontend build is verified only when:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd run build
```

exits successfully and creates `C:\Hackathon\esg-engine\site\dist`.

The dev server is verified only when:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd run dev
```

serves the app and the browser shows:

- the persistent `SYNTHETIC DEMONSTRATION DATA` banner;
- the hero section;
- a readable virtualized leaderboard;
- a company detail view after selecting a row;
- responsive layouts at desktop, tablet, and mobile widths.

