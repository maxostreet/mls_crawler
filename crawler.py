from bs4 import BeautifulSoup
from urllib2 import urlopen
import csv
import pprint
import collections

URL = "http://v3.torontomls.net/Live/Pages/Public/Link.aspx?Key=0c46e2aed7604e3ca10d56abf498a599&App=TREB"
CSV_FILE = "data.csv"

DATA_FIELDS = {
        "mls_num" : "MLS#:",
        "seller" : "Seller:",
        "sold_price" : "Sold:",
        "fronting_on": "Fronting On:",
        "acreage": "Acreage:",
        "rms" : "Rms:",
        "bedrooms" : "Bedrooms:",
        "washrms" : "Washrms:",
        "occupancy" : "Occupancy:",

        "coop_brokerages" : "Co-Op:",
        "contract_date" : "Contract Date:",
        "expiry_date" : "Expiry Date:",
        "last_update" : "Last Update:",
        "sold_date" : "Sold Date:",
        "closing_date": "Closing Date:",
        "cb_comm" : "CB Comm:",

        }

def extract_report(report):
    extracted_data = {}

    # get address info
    street = report.find("span", "formfield")
    infos = [info.string for info in street.parent.parent.parent.find_next_sibling("div", "formgroup").find_all("span", "value")]
    extracted_data["street"] = street.string
    extracted_data["city"] = infos[0]
    extracted_data["province"] = infos[1]
    extracted_data["postal"] = infos[2]

    # get all the other infos as specifed in DATA_FIELDS
    for search_key in DATA_FIELDS:
        value = report.find(text=DATA_FIELDS[search_key]).parent.find_next_sibling(True, "value").string
        extracted_data[search_key] = value

    salesperson_data = [ str(result.string) for result in report.find_all("a", "value")]
    data_heading = "list_brokerage"
    for index, data in enumerate(salesperson_data):
        if data == "None":
            continue
        if index == 0:
            extracted_data[data_heading] = data
            data_heading = "list_salespersons"
            extracted_data[data_heading] = []
            continue
        if data == extracted_data["coop_brokerages"]:
            data_heading = "coop_salespersons"
            extracted_data[data_heading] = []
            continue

        extracted_data[data_heading].append(data)


    # sort by key before return
    extracted_data = collections.OrderedDict(sorted(extracted_data.items()))

    return extracted_data



def write_to_csv(results):
    # print collections.OrderedDict(sorted(s()))

    column_headings = results[0].keys()
    with open(CSV_FILE, 'wb') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=column_headings, dialect='excel')
        writer.writeheader()
        for data in results:
            writer.writerow(data)



if __name__ == "__main__":
    html = urlopen(URL).read()
    soup = BeautifulSoup(html, "lxml")
    reports = [ report_container for report_container in soup.findAll("div", "link-item") ]
    report_len = len(reports)
    results = []

    for index,report in enumerate(reports):
        if report.get("data-deferred-loaded") is not None:
            reports[index] = report.get('data-deferred-loaded')
        else:
            reports[index] = report.get('data-deferred-load')

    for index, report_url in enumerate(reports):
        print index,"/",report_len,": ", report_url
        html = urlopen(report_url).read()
        soup = BeautifulSoup(html, "lxml")
        report = soup.find("div", "legacyBorder")
        data = extract_report(report)
        results.append(data)
    write_to_csv(results)