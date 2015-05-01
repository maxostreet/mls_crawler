from bs4 import BeautifulSoup
from urllib2 import urlopen
import sys
import csv
import pprint
import collections
import time

# URL = "http://v3.torontomls.net/Live/Pages/Public/Link.aspx?Key=0c46e2aed7604e3ca10d56abf498a599&App=TREB"
# CSV_FILE = "mls_data.csv"
INPUT_FILE = "./urls.txt"

DATA_FIELDS = {
    "mls_num": "MLS#:",
    "seller": "Seller:",
    "sold_price": "Sold:",
    "list_price": "List:",
    "percent_diff": "% Dif:",
    "dom": "DOM:",
    # "taxes" : "Taxes:",
    "fronting_on": "Fronting On:",
    "acreage": "Acreage:",
    "Lot": "Irreg:",
    "rms": "Rms:",
    "bedrooms": "Bedrooms:",
    "washrms": "Washrms:",
    "occupancy": "Occupancy:",

    "coop_brokerages": "Co-Op:",
    "contract_date": "Contract Date:",
    "expiry_date": "Expiry Date:",
    "last_update": "Last Update:",
    "sold_date": "Sold Date:",
    "closing_date": "Closing Date:",
    "cb_comm": "CB Comm:",
}

extracted_data = {}


def get_address_info(report):
    # get address info
    street = report.find("span", "formfield")
    infos = [info.string for info in
             street.parent.parent.parent.find_next_sibling("div", "formgroup").find_all("span", "value")]
    extracted_data["street"] = street.string
    extracted_data["city"] = infos[0]
    extracted_data["province"] = infos[1]
    extracted_data["postal"] = infos[2]


def get_taxes(report):
    global extracted_data
    tax_and_year = [e.string for e in report.find(
        text="Taxes:").parent.parent.parent.find_all("span", "value")]
    if tax_and_year[1] is not None:
        extracted_data["taxes"] = tax_and_year[0] + " / " + tax_and_year[1]
    else:
        extracted_data["taxes"] = tax_and_year[0] + " / "


def get_building_style_and_type(report):
    global extracted_data
    style_and_type = [e.string for e in
                      report.find(text="Irreg:").parent.parent.find_all_previous("span", "value", limit=2)]
    extracted_data['building_style'] = style_and_type[0]
    extracted_data['building_type'] = style_and_type[1]


def get_dimensions(report):
    global extracted_data
    dimension = report.find(text="Acreage:")
    if dimension is not None:
        dimension = dimension.parent.parent.parent.find_all(
            True, "value")[-1].string
        extracted_data['dimension'] = dimension
    else:
        dimension = report.find(text="Lot:").parent.parent.find(
            True, "value").string
        extracted_data['dimension'] = dimension


def extract_report(report):
    global extracted_data

    get_address_info(report)
    get_taxes(report)
    get_building_style_and_type(report)
    get_dimensions(report)

    # get all the other infos as specifed in DATA_FIELDS
    for search_key in DATA_FIELDS:
        try:
            value = report.find(text=DATA_FIELDS[search_key]).parent.find_next_sibling(
                True, "value").string
            extracted_data[search_key] = value
        except Exception:
            extracted_data[search_key] = ""

    salesperson_data = [str(result.string)
                        for result in report.find_all("a", "value")]
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


def write_to_csv(filename, results):
    column_headings = results[0].keys()
    with open(filename, 'wb') as output_file:
        writer = csv.DictWriter(
            output_file, fieldnames=column_headings, dialect='excel')
        writer.writeheader()
        for data in results:
            writer.writerow(data)


def scrape_url(url, url_index):
    output_csv_file = "mls_data_%d.csv" % url_index
    html = urlopen(url).read()
    soup = BeautifulSoup(html, "html.parser")
    reports = [
        report_container for report_container in soup.findAll("div", "link-item")]
    report_len = len(reports)
    results = []

    for index, report in enumerate(reports):
        if report.get("data-deferred-loaded") is not None:
            reports[index] = report.get('data-deferred-loaded')
        else:
            reports[index] = report.get('data-deferred-load')

    for index, report_url in enumerate(reports):
        print index, "/", report_len, ": ", report_url
        html = urlopen(report_url).read()
        soup = BeautifulSoup(html, "html.parser")
        report = soup.find("div", "legacyBorder")
        data = extract_report(report)
        results.append(data)
    write_to_csv(output_csv_file, results)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Need the filename!"
        sys.exit()

    filename = sys.argv[1]
    # filename = INPUT_FILE
    with open(filename) as f:
        for i, url in enumerate(f):
            print "PROCESSING URL %d: %s" % (i, url)
            scrape_url(url, i)
            print "DONE URL ", i
