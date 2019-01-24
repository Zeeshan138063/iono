# for gmail and google app
#
import keyring

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER =  'digisuperstar@gmail.com'
EMAIL_HOST_PASSWORD = 'testing1234'
# keyring.set_password("system",EMAIL_HOST_USER,EMAIL_HOST_PASSWORD)

EMAIL_PORT = 587

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


