# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: A
      - heading "Acenta Master" [level=1] [ref=e7]
      - paragraph [ref=e8]: Acenta operasyonlarını tek panelden yönet.
    - generic [ref=e9]:
      - generic [ref=e11]: Giriş Yap
      - generic [ref=e13]:
        - generic [ref=e14]:
          - text: Email
          - textbox "Email" [ref=e15]:
            - /placeholder: ornek@acenta.com
            - text: admin@acenta.test
        - generic [ref=e16]:
          - text: Şifre
          - textbox "Şifre" [ref=e17]: admin123
        - button "Giriş Yap" [ref=e18] [cursor=pointer]
        - generic [ref=e19]: "Demo: admin@acenta.test / admin123"
  - region "Notifications alt+T"
```