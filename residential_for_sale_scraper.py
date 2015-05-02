from bs4 import BeautifulSoup
from urllib2 import urlopen
import csv
import collections
import sys
import re

# URL = "http://v3.torontomls.net/Live/Pages/Public/Link.aspx?Key=98e9e0a5c3474296ab955d0eff74d627&App=TREB"
DATA_FIELDS = {
    "mls_num": "MLS#:",
    "pin_num": "PIN#:",
    "arn_num": "ARN#:",
    "sellers": re.compile('Seller.:'),
    "sold_price": "Sold:",
    "list_price": "List:",
    "percent_diff": "%Dif:",
    "dom": "DOM:",
    "occupancy": "Occup:",
    "possession": "Possession:",
    "holdover": "Holdover:",
    "spis": "SPIS:",
    "sold_area": "Sld Area:",

    "total_area": "Total Area:",
    "zoning": "Zoning:",
    "truck_level": "Truck Level:",
    "garage_type": "Garage Type:",

    "coop_brokerages": "Co-Op:",
    "sold_date": "Sold Date:",
    "closing_date": "Closing Date:",
    "contract_date": "Contract Date:",
    "expiry_date": "Expiry Date:",
    "cb_comm": "CB Comm:",
    "leased_terms": "Leased Terms:"

    # custom fields:
    # street
    # city
    # province
    # postal
    # list_brokerage
    # list_salespersons
    # coop_salespersons
}

extracted_data = {}


def get_address_info(report):
    # get address info
    street = report.find("span", "formfield")
    unit = street.find_next_sibling("span", "formfield")
    infos = [info.string for info in
             street.parent.parent.parent.find_next_sibling("div", "formgroup").find_all("span", "value")]
    extracted_data["street"] = street.string
    if unit.string is not None:
        extracted_data["street"] += " " + unit.string
    extracted_data["city"] = infos[0]
    extracted_data["province"] = infos[1]
    extracted_data["postal"] = infos[2]


def get_taxes(report):
    global extracted_data
    extracted_data["taxes"] = ''
    tax_and_year = [e.string or "" for e in report.find(
        text="Taxes:").parent.parent.parent.find_all("span", "value")]
    if len(tax_and_year) == 2:
        extracted_data["taxes"] = tax_and_year[0] + " / " + tax_and_year[1]
    elif len(tax_and_year) == 3:
        extracted_data["taxes"] = tax_and_year[0] + " / " + \
            tax_and_year[1] + " / " + tax_and_year[2]
    else:
        extracted_data["taxes"] = tax_and_year[0] + " / "


def get_building_info_and_type(report):
    global extracted_data
    extracted_data['building_style'] = ''
    style_and_type_content = report.find(
        text="Lot:") or report.find(text="Irreg:")
    print style_and_type_content
    if style_and_type_content is None:
        return

    style_and_type = [e.string or '' for e in
                      style_and_type_content.parent.parent.find_all_previous("span", "value", limit=2)]

    extracted_data['building_style'] = style_and_type[
        0] + " " + style_and_type[1]


def get_salespersons(report_html):
    salesperson_data = [str(result.string)
                        for result in report_html.find_all("a", "value")]
    extracted_data["list_brokerage"] = ''
    extracted_data["list_salespersons"] = ''
    extracted_data["coop_salespersons"] = ''
    data_heading = "list_brokerage"
    for index, data in enumerate(salesperson_data):
        if data == "None":
            continue
        elif index == 0:
            extracted_data[data_heading] = data
            data_heading = "list_salespersons"
            extracted_data[data_heading] = []
        elif data == extracted_data["coop_brokerages"]:
            data_heading = "coop_salespersons"
            extracted_data[data_heading] = []
        extracted_data[data_heading].append(data)


def extract_report(report_url):
    global extracted_data
    html = urlopen(report_url).read()
    scraper = BeautifulSoup(html, "html.parser")
    report_html = scraper.find("div", "legacyBorder")

    get_address_info(report_html)
    get_taxes(report_html)
    get_building_info_and_type(report_html)

    for search_key in DATA_FIELDS:
        try:
            value = report_html.find(
                text=DATA_FIELDS[search_key]).parent.find_next_sibling(True, "value").string
            extracted_data[search_key] = value
        except Exception:
            extracted_data[search_key] = ""

    get_salespersons(report_html)
    return collections.OrderedDict(sorted(extracted_data.items()))


def extract_reports(reports):
    num_reports = len(reports)
    results = []
    for index, report in enumerate(reports):
        reports[index] = report.get(
            'data-deferred-loaded') or report.get('data-deferred-load')
        print index, "/", num_reports, ": ", reports[index]
        results.append(extract_report(reports[index]))
    return results


def write_to_csv(filename, results):
    """write results to a csv file"""
    column_headings = results[0].keys()
    with open(filename, 'wb') as output_file:
        writer = csv.DictWriter(
            output_file, fieldnames=column_headings, dialect='excel')
        writer.writeheader()
        for data in results:
            writer.writerow(data)


def scrape_url(url, report_index):
    """ main function to scrape the html of a url """
    output_csv_file = "for_sale_residential_%d.csv" % report_index
    html = urlopen(url).read()
    scraper = BeautifulSoup(html, "html.parser")
    reports = [
        report_container for report_container in scraper.findAll("div", "link-item")]
    results = extract_reports(reports)
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
