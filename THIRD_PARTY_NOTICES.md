# Third-party notices

Velo is distributed under the MIT License. Its packaged Windows builds also contain third-party software. Release builds collect the license files shipped by the installed Python distributions into the `licenses` folder next to `Velo.exe`.

The direct runtime dependencies are:

| Component | Version | License |
|---|---:|---|
| aiohttp | 3.13.5 | Apache-2.0 AND MIT |
| pystray | 0.19.5 | LGPL-3.0 |
| Pillow | 11.3.0 | MIT-CMU |
| pywebview | 6.2.1 | BSD-3-Clause |
| pywin32 | 312 | PSF-2.0 |

Packaged transitive dependencies include aiohappyeyeballs, aiosignal, async-timeout, attrs, bottle, cffi, clr-loader, frozenlist, idna, multidict, propcache, proxy_tools, pycparser, pythonnet, six, typing-extensions, and yarl. Their exact versions are recorded in `requirements-lock.txt`, and their available license or notice files are included in packaged builds by `scripts/collect_licenses.py`.

Source code for Velo and the dependency list used to construct each release are available at <https://github.com/aechXIII/Velo>. Source code for pystray is available from <https://github.com/moses-palmer/pystray> under the LGPL-3.0 terms included with the distribution.

Third-party names and trademarks belong to their respective owners. Inclusion does not imply endorsement.
