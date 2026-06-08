# Brand images

Home Assistant loads integration logos/icons from the
[`home-assistant/brands`](https://github.com/home-assistant/brands) repository
(served via `brands.home-assistant.io`), **not** from the integration package.

These files are kept here version-controlled and ready to submit:

```
custom_integrations/pinpaw/
├── icon.png       # 256×256
└── icon@2x.png    # 512×512
```

## How to publish the logo

1. Fork `home-assistant/brands`.
2. Copy `custom_integrations/pinpaw/` into the fork at the same path.
3. Open a PR. Their CI checks dimensions and that `@2x` is exactly double.

Until that PR is merged, the integration works fully but shows the default
Home Assistant icon instead of the PinPaw logo.
