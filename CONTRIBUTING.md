# Contributing

Thanks for helping. This is a demo repository, so changes that make it easier to install, understand or present are
the most welcome.

- **Bugs and questions:** open an issue with your OS, `exakit --version`, the command you ran and its output.
- **Pull requests:** keep them small and focused. Before opening one:
  - run the checks in [VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md) that apply to your change (at least
    `python3 -m py_compile` on changed Python files and `bash -n` on changed scripts);
  - keep all data synthetic: no real people, employers, banks, phone numbers or email domains (use `example.com`);
  - never commit anything from `secrets/`, `config.local.env` or `.work/`.
- **Style:** follow the code around your change: settings in `config.env`, shell helpers in `setup/common.sh`,
  SQL for the service in `service/sqlq.py`.

By contributing you agree that your contribution is licensed under the MIT license of this repository, and to follow
the [Code of Conduct](CODE_OF_CONDUCT.md).
