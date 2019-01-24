import re
import pandas as pd
import yagmail
from django.conf import settings
from datetime import datetime

from rest_framework.decorators import api_view

from plantedge.models import Subscriber, Plots, Alert


@api_view(['POST'])
def send_email_cron(request):
    MEDIA_ROOT = getattr(settings, "MEDIA_ROOT", None)

    media_root = MEDIA_ROOT

    subscribers = Subscriber.objects.all()
    for subscriber in subscribers:
        plot_alerts = pd.read_json(subscriber.plot_alert_json, keep_default_dates=False)._get_values
        contents = []
        now = datetime.now()
        alert_date = "<h1>Alert Date : "+str(now.strftime("%A,%d %B %Y"))+" </h1><br/>"
        header = "\t<p>Alerts type</p> <p> Geojson</p><br/>"
        rows = '<tr style="text-align: left;"><th  style ="border: 1px solid black;">Alert Type</th><th  style ="border: 1px solid black;">Geojson</th></tr>'
        contents.append(header)

        for plot_alert in plot_alerts:
            alerts = Alert.objects.filter(plot=plot_alert[2])
            if alerts.first() is not None:
                # json_file_name = plot.file

                for alert_type in  plot_alert[0]:
                    if alert_type :

                        type_filtered_alerts  = alerts.filter(type__icontains=alert_type)
                        for type_filtered_alert in type_filtered_alerts:

                            file_link =media_root+str(type_filtered_alert.file_path)

                            record = "\t"+alert_type+"\t\t\t\t\t<a href="+file_link+">Download</a><br/>"
                            rows+='<tr style="text-align: left;"><td style ="border: 1px solid black;" >'+alert_type+'</td><td  style ="border: 1px solid black;"><a href="'+file_link+'">Download</a></td></tr>'
                            # html_part = MIMEMultipart(_subtype='related')
                            # body = MIMEText('<p><a href=file_link/></p>', _subtype='html')
                            contents.append(record)
                    else:
                        continue

                html = alert_date
                # html += '<table style="width:100% ; border: 1px solid black">'+rows+'</table>'
                html += '<table style="font-family: arial, sans-serif;border-collapse: collapse;width: 100%;">'+rows+'</table>'
                email_receiver = subscriber.email
                yagEmail( email_receiver,html)


def yagEmail(receiver,contents):
    EMAIL_HOST_PASSWORD = getattr(settings, "EMAIL_HOST_PASSWORD", None)
    EMAIL_HOST_USER = getattr(settings, "EMAIL_HOST_USER", None)
    now = datetime.now()
    subject = re.sub("#ALlert Date : #", '', 'Alert Date : ' + str(now.strftime("%A,%d %B %Y")))
    # yagmail.register(self.EMAIL_HOST_USER,self.EMAIL_HOST_PASSWORD)
    # create server object; can be reused
    yag = yagmail.SMTP(EMAIL_HOST_USER,EMAIL_HOST_PASSWORD)
    yag.send(to=receiver,subject=subject,contents=contents)
    return
