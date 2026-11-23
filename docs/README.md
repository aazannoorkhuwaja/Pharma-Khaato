# Pharma Khaato documentation

| I want to… | Start here |
| --- | --- |
| Install or upgrade | [Installer downloads](../README.md#install) · [Upgrade from 2.5.0](UPGRADE_2_5_1.md) |
| Make my first practice sale | [Try the app](TRY_IT.md) |
| Run a shift and look up everyday tasks | [Operator quick start](OPERATOR_QUICK_START.md) · [User guide](USER_GUIDE.md) |
| Decide whether a shop can go live | [Shop trial](SHOP_TRIAL.md) · [Site acceptance](PHARMACY_SITE_ACCEPTANCE.md) · [Readiness guide](REAL_WORLD_READINESS.md) |
| Report a problem | [Support](../SUPPORT.md) · [Security reporting](../SECURITY.md) |
| Understand or change the application | [Architecture](ARCHITECTURE.md) · [Database](DATABASE.md) · [Developer workflow](DEVELOPER_WORKFLOW.md) · [Testing](TESTING.md) |
| Build and distribute installers | [Deployment](DEPLOYMENT.md) · [Windows delivery](WINDOWS_DELIVERY.md) · [Release approval](RELEASE_APPROVAL_GATE.md) · [Release procedure](RELEASING.md) · [Updates](UPDATES.md) |
| Find a previous release | [Published releases](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases) · [Historical release notes](releases/) |

## Source directories

| Directory | Contents |
| --- | --- |
| [ui](../ui/) | PySide6 windows, screens and widgets |
| [controllers](../controllers/) | Entry points for application actions from the UI |
| [core](../core/) | Business logic and application services |
| [models](../models/), [database](../database/), [migrations](../migrations/) | Data models, database infrastructure and versioned schema changes |
| [tests](../tests/) | Automated regression tests |
| [packaging](../packaging/), [scripts](../scripts/), [workflows](../.github/workflows/) | Platform packaging resources, maintenance tools and CI |
