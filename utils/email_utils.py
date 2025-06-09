import smtplib as sm
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import ftfy
import logging

logger = logging.getLogger(__name__)

def first_draft(order, first_name, db, store, order_country):
    draft = {}

    intro, content, end = "", "", ""

    if store == 'EU' and order_country == 'DE':
        draft['Subject'] = f"Bestellung {order['Order Number']} sicher erhalten, wir bearbeiten sie :)" 

        intro = f"""<p> Sehr geehrter {first_name}, <br><br> Vielen Dank für Ihren Einkauf bei ML Performance und wir hoffen, dass es Ihnen gut geht. <br><br>
                Wir möchten Ihnen mitteilen, dass Ihre Bestellung(en) sicher bei uns eingegangen sind und wir diese so schnell wie möglich bearbeiten werden. 
                Unten finden Sie den aktuellen Lagerstatus für alle Ihre Bestellungen, die ich vorliegen habe. 
                Ich werde Sie weiterhin mit Updates versorgen, bis Sie alles sicher erhalten haben.
                Wir werden die Bestellung erst versenden, wenn alle Artikel in der Bestellung fertig sind.<br></p>"""
        
        content = """<table style='width: 60%;border-collapse: collapse;'><tr>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Bestellung </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:85px;width: 50%;'> Artikel </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Menge </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:40px;width: 20%;'> Voraussichtliches Versanddatum </td></tr>"""
        
        end = f"""</table> <br> Bitte zögern Sie nicht, sich bei Fragen an mich zu wenden. Ich helfe Ihnen gerne weiter! :) <br> 
                <br> Mit freundlichen Grüßen, """
        
    else:
        draft['Subject'] = f"Order {order['Order Number']} Safely Received, We Are Processing It :)"

        intro = f"""<p> Dear {first_name}, <br><br> Many thanks for shopping with ML Performance and we hope you are keeping well. <br><br>
                Just wish to update you that your order(s) has been safely received and we will be processing them as soon as possible. 
                Please find below the current stock status for all your orders that I have in hand – 
                I will be working on providing you with more updates along the way until you have safely received everything.  
                We will only dispatch the order once all the items in the order are ready.<br></p>"""
        
        content = """<table style='width: 60%;border-collapse: collapse;'><tr>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Order </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:85px;width: 50%;'> Item </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Quantity </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:40px;width: 20%;'> Estimated Dispatch Date  </td></tr>"""
        
        end = f"""</table> <br> Please do not hesitate to give me a shout if you have any queries and I will be happy to assist! :) <br> 
                    <br> Kind Regards, """
        
    table_content = ''
    for item in order['Line Items']:
        table_content += f"""<tr><td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{order['Order Number']}</td>
                    <td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{item['title']}</td>
                    <td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{item['quantity']}</td>
                    <td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{item['Latest ETA On Hand']}</td></tr>"""
        

    signature = f"""<br> Angela Amado | {db['COMPANY']}<br>T: {db['PHONE']}<br> E: {db['SENDER_EMAIL']}<br> W: {db['WEBSITE']}<br>"""

    draft['html'] = ftfy.fix_text(intro + content + table_content + end + signature)
    return draft

def follow_up_draft(order, first_name, db, store, order_country):
    draft = {}

    intro, content, end = "", "", ""

    if store == 'EU' and order_country == 'DE':
        draft['Subject'] = f"Order {order['Order Number']} Update {datetime.today().strftime('%d-%m-%Y')}" 
        
        intro = f"""<p> Sehr geehrter {first_name}, <br><br> FIm Anschluss an meine vorherige E-Mail habe ich Ihre Bestellung weiterverfolgt. 
                            Bitte finden Sie unten den aktualisierten Lagerstatus für alle Ihre Bestellungen, die ich vorliegen habe. 
                            Seien Sie versichert, dass ich weiterhin daran arbeiten werde, Ihnen mehr Updates zu geben, bis Sie alles sicher erhalten haben. 
                            Wir werden die Bestellung erst versenden, wenn alle Artikel in der Bestellung fertig sind. <br><br> 
                            Ich entschuldige mich für eventuelle Verzögerungen und habe dem Versand mitgeteilt, 
                            dass diese Bestellung sofort am nächsten Tag geliefert werden sollte, sobald wir sie erhalten. <br></p>"""
        
        content = """<table style='width: 60%;border-collapse: collapse;'><tr>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Bestellung </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:85px;width: 50%;'> Artikel </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Menge </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:40px;width: 20%;'> Voraussichtliches Versanddatum </td></tr>"""
        
        end = f"""</table> <br> Bitte zögern Sie nicht, sich bei Fragen an mich zu wenden. Ich helfe Ihnen gerne weiter! :) <br> 
                <br> Mit freundlichen Grüßen, """
        
    else:
        draft['Subject'] = f"Order {order['Order Number']} Update {datetime.today().strftime('%d-%m-%Y')}" 

        intro = f"""<p> Dear {first_name}, <br><br> Many thanks for shopping with ML Performance and we hope you are keeping well. <br><br>
                Just wish to update you that your order(s) has been safely received and we will be processing them as soon as possible. 
                Please find below the current stock status for all your orders that I have in hand – 
                I will be working on providing you with more updates along the way until you have safely received everything.  
                We will only dispatch the order once all the items in the order are ready.<br></p>"""
        
        content = """<table style='width: 60%;border-collapse: collapse;'><tr>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Order </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:85px;width: 50%;'> Item </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:5px;width: 15%;'> Quantity </td>
                <td style='border: 1px solid black;padding-left:5px;padding-right:40px;width: 20%;'> Estimated Dispatch Date  </td></tr>"""
        
        end = f"""</table> <br> Please do not hesitate to give me a shout if you have any queries and I will be happy to assist! :) <br> 
                    <br> Kind Regards, """
        
    table_content = ''
    for item in order['Line Items']:
        table_content += f"""<tr><td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{order['Order Number']}</td>
                    <td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{item['title']}</td>
                    <td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{item['quantity']}</td>
                    <td style='border: 1px solid black;padding-left:5px;padding-right:5px;'>{item['Latest ETA On Hand']}</td></tr>"""
        

    signature = f"""<br> Angela Amado | {db['COMPANY']}<br>T: {db['PHONE']}<br> E: {db['SENDER_EMAIL']}<br> W: {db['WEBSITE']}<br>"""

    draft['html'] = ftfy.fix_text(intro + content + table_content + end + signature)
    return draft


def send_email(recipient, draft, db):
    try:
        s = sm.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.ehlo()

        sender = db['SENDER_EMAIL']
        password = db['SENDER_PASSWORD']

        # sender = 'iffah@mlperformance.co.uk'
        # password = "owee xytq urot uthi" #IffahMLP!
        # recipient = 'iffah@mlperformance.co.uk'

        s.login(sender, password)

        msg = MIMEMultipart()
        msg['Subject'] = draft['Subject']
        msg['From'] = sender
        msg['To'] = recipient

        content = MIMEText(draft['html'], 'html')
        msg.attach(content)

        s.sendmail(sender, recipient, msg.as_string())
        s.quit()
        logger.info(f"Email sent to {recipient}")

    except Exception as e:
        logger.error(f"Error sending email to {recipient}: {str(e)}")
