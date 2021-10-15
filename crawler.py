import sys
import xml
import json
import time
import urllib.request
from urllib.error import HTTPError
from optparse import OptionParser
import xml.etree.ElementTree as ET
from lxml import etree
from urllib import request
import os
import matplotlib
from urllib.parse import urlparse

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'

def create_folder(name, demo_name):
    os.mkdir(name)
    os.mkdir(name+"/controllers")
    os.mkdir(name+"/data")
    os.mkdir(name+"/models")
    os.mkdir(name+"/static")
    os.mkdir(name+"/static/img")
    os.mkdir(name+"/views")

    init_model = open(os.path.join(name+"/models","__init__.py"),"w")
    init_model_body = "from . import product_template"
    init_model.write(init_model_body)
    init_model.close()

    product_template_model = open(os.path.join(name+"/models","product_template.py"),"w")
    product_template_body = """from odoo import fields, models
from odoo.tools.translate import html_translate
class ProductTemplate(models.Model):
    _inherit = "product.template"
    website_description = fields.Html(
        "Website description for the website", sanitize_attributes=False, translate=html_translate
    )
    """
    product_template_model.write(product_template_body)
    product_template_model.close()

    product_views = open(os.path.join(name+"/views","product_view.xml"),"w")
    product_views_body = """<?xml version="1.0" ?>
<odoo>
    <data>
        <record id="product_template_form_view_inherit_website_sale_stock" model="ir.ui.view">
            <field name="name">product.template.form.inherit.website.sale.stock</field>
            <field name="model">product.template</field>
            <field name="inherit_id" ref="website_sale.product_template_form_view" />
            <field name="arch" type="xml">
                <group name="shop" position="after">
                    <group string="Website description">
                        <field name='website_description' nolabel="1" />
                    </group>
                </group>
            </field>
        </record>
    </data>
</odoo>
    """
    product_views.write(product_views_body)
    product_views.close()

    init = open(os.path.join(name,"__init__.py"),"w")
    init_body = "from . import models"
    init.write(init_body)
    init.close()

    manifest = open(os.path.join(name,"__manifest__.py"),"w")
    manifest_body = """{
    'name': '"""+ fix_folder_name(name) +"""',
    'version': '1.0',
    'category': 'Apps/Data',
    'depends': ['base', 'mail', 'uom', 'website_sale_stock'],
    'data': [
        'views/product_view.xml',
        'data/"""+ demo_name +"""'
    ],
    'installable': True,
    'auto_install': False,
}"""
    manifest.write(manifest_body)
    manifest.close()

def CDATA(text=None):
    element = ET.Element('![CDATA[')
    element.text = text
    return element

ET._original_serialize_xml = ET._serialize_xml
def _serialize_xml(write, elem, qnames, namespaces,short_empty_elements, **kwargs):
    if elem.tag == '![CDATA[':
        write("\n<%s%s]]>\n" % (
                elem.tag, elem.text))
        return
    return ET._original_serialize_xml(
        write, elem, qnames, namespaces,short_empty_elements, **kwargs)
ET._serialize_xml = ET._serialize['xml'] = _serialize_xml

def get_page(url, collection_handle=None):
    full_url = url
    if collection_handle:
        full_url += '/collections/'+collection_handle
    full_url += '/products.json'
    req = urllib.request.Request(
        full_url,
        data=None,
        headers={'User-Agent': USER_AGENT}
    )
    while True:
        try:
            data = urllib.request.urlopen(req).read()
            break
        except HTTPError:
            print('Blocked! Sleeping... get page')
            time.sleep(180)
            print('Retrying')

    products = json.loads(data.decode())['products']
    return products

def get_page_collections(url):
    full_url = url + '/collections.json'
    page = 1
    while True:
        req = urllib.request.Request(
            full_url + '?page={}'.format(page),
            data=None,
            headers={
                'User-Agent': USER_AGENT
            }
        )
        while True:
            try:
                data = urllib.request.urlopen(req).read()
                break
            except HTTPError:
                print('Blocked! Sleeping...')
                time.sleep(180)
                print('Retrying')

        cols = json.loads(data.decode())['collections']
        if not cols:
            break
        for col in cols:
            yield col
        page += 1

def check_shopify(url):
    try:
        get_page(url, 1)
        return True
    except Exception:
        return False


def fix_url(url):
    fixed_url = url.strip()
    if not fixed_url.startswith('http://') and \
       not fixed_url.startswith('https://'):
        fixed_url = 'https://' + fixed_url

    return fixed_url.rstrip('/')

def check_id(id, results):
    for result in results:
        if result:
            if result['id'] == id:
                return True
    return False

def fix_folder_name(name):
    str_name = name.split("_")
    i = 0
    for str_value in str_name:
        str_name[i] = str_value.capitalize()
        i+=1
    name = " ".join(str_name)
    return name

# validate description
def validate_des(des):
    while des.find('[') != -1 and des.find(']') != -1:
        f = des.find('[')
        fd = des.find(']')
        des = des.replace(des[des.find('['):des.find(']')+1],'')
    return des

# crawler images
def crawl_image(url,folder_name):
    output_dir = folder_name+'/static/img'
    image_url = url
    validate = image_url.rfind('?')
    image_url = image_url[:validate]
    domain = urlparse(image_url).netloc
    domain = "https://" + domain
    output_dir += image_url.replace(domain,'')
    output_dir = output_dir.replace(os.path.basename(image_url),'')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # save path
    image_save_path = output_dir+ os.path.basename(image_url)
    # Download file from url
    request.urlretrieve(image_url, image_save_path)
    result = folder_name+'/static/img'+ image_url.replace(domain,'')
    return result

def extract_products_collection(url, col):
    products = get_page(url, col)
    results=['']
    for product in products:
        product_id = product['id']
        if check_id(product_id, results):
            for result in results:
                if result:
                    if result['id'] == product_id:
                        result['collections'] += (product['product_type'])
        else:
            rows = {'id': product['id'],
                        'title': product['title'],
                        'brand': product['vendor'],
                        'category': col,
                        "collections": product['product_type'],
                        "tags": product['tags'],
                        "variants": product['variants'],
                        "options": product['options'],
                        "images": product['images'],
                        "description": product['body_html']}
            results.append(rows)
    for result in results:
        if result == '':
            results.remove(result)
    return results

def check_product_variant(name):
    if name.lower() == "size" or name.lower() == "color":
        return True
    return False

def validate_variant_name(name):
    result = name.replace(' ', '_')
    result = (result.replace('/', '_')).lower()
    return result

def extract_products(url, folder_name, path, collections=None):
    with open(os.path.join(folder_name+"/data",path), 'wb') as f:
        # initializing root
        print("initializing root")
        root = ET.Element("odoo")
        ET.tostring(root, encoding='utf8', method='xml')
        root_data = ET.SubElement(root, "data", noupdate = "1")
        attribute_record_values = [{"name": 'Size', "values": ['']},{"name":'Color', "values": ['']},{"name": 'Material', "values": ['']}]
        for col in get_page_collections(url):
            if collections and col['handle'] not in collections:
                continue
            for product in extract_products_collection(url, col['handle']):
                print("processing attribute.  ")
                for option in product['options']:
                    print("processing attribute . ")
                    for value in option['values']:
                        print("processing attribute  .")
                        if option['name'].lower() == 'size':
                            if not value in attribute_record_values[0]['values']:
                                attribute_record_values[0]['values'].append(value)
                        elif option['name'].lower() == 'color':
                            if not value in attribute_record_values[1]['values']:
                                attribute_record_values[1]['values'].append(value)
                        elif option['name'].lower() == 'material':
                            if not value in attribute_record_values[1]['values']:
                                attribute_record_values[2]['values'].append(value)
            for attribute_record_value in attribute_record_values:
                attribute_record_value['values'] = list(filter(None, attribute_record_value['values']))

        # export atribute to xml
        print("initializing attribute records")
        for attribute_record_value in attribute_record_values:
            sequence = 1
            attribute_record = ET.SubElement(root_data, "record", id = "product_attribute_"+ validate_variant_name(attribute_record_value['name']), model="product.attribute")
            ET.SubElement(attribute_record, "field", name="name").text = attribute_record_value['name']
            if attribute_record_value['name'].lower() == 'size':
                ET.SubElement(attribute_record, "field", name="display_type").text = 'radio'
                for value in attribute_record_value['values']:
                    attribute_value_record = ET.SubElement(root_data, "record", id = "product_attribute_value_"+ validate_variant_name(attribute_record_value['name']) +"_"+ validate_variant_name(value), model="product.attribute.value")
                    ET.SubElement(attribute_value_record, "field", name="name").text = value
                    ET.SubElement(attribute_value_record, "field", name="attribute_id", ref="product_attribute_"+ attribute_record_value['name'].lower())
                    ET.SubElement(attribute_value_record, "field", name="sequence").text = str(sequence)
                    sequence += 1
            elif attribute_record_value['name'].lower() == 'color':
                ET.SubElement(attribute_record, "field", name="display_type").text = 'color'
                for value in attribute_record_value['values']:
                    attribute_value_record = ET.SubElement(root_data, "record", id = "product_attribute_value_"+ validate_variant_name(attribute_record_value['name']) +"_"+ validate_variant_name(value), model="product.attribute.value")
                    ET.SubElement(attribute_value_record, "field", name="name").text = value
                    try:
                        color = matplotlib.colors.cnames[validate_variant_name(value)]
                    except:
                        color = "#ffffff"
                    ET.SubElement(attribute_value_record, "field", name="html_color").text = color
                    ET.SubElement(attribute_value_record, "field", name="attribute_id", ref="product_attribute_"+ attribute_record_value['name'].lower())
                    ET.SubElement(attribute_value_record, "field", name="sequence").text = str(sequence)
                    sequence += 1
            elif attribute_record_value['name'].lower() == 'material':
                ET.SubElement(attribute_record, "field", name="display_type").text = 'radio'
                for value in attribute_record_value['values']:
                    attribute_value_record = ET.SubElement(root_data, "record", id = "product_attribute_value_"+ validate_variant_name(attribute_record_value['name']) +"_"+ validate_variant_name(value), model="product.attribute.value")
                    ET.SubElement(attribute_value_record, "field", name="name").text = value
                    ET.SubElement(attribute_value_record, "field", name="attribute_id", ref="product_attribute_"+ attribute_record_value['name'].lower())
                    ET.SubElement(attribute_value_record, "field", name="sequence").text = str(sequence)
                    sequence += 1
        print("initializing collection records")
        collections_root = ET.Element("odoo")
        collection_count = 1
        product_count = 1
        for col in get_page_collections(url):
            if collections and col['handle'] not in collections:
                continue
            # export collection to xml
            collection_record = ET.SubElement(root_data, "record", id = "product_category_"+col['handle'], model="product.public.category")
            ET.SubElement(collection_record, "field", name="name").text = col['title']


            for product in extract_products_collection(url, col['handle']):
                variant_check = True
                # check product_variant?
                if check_product_variant(product['options'][0]['name']):
                    print("processing file export. .")
                    # export product to xml
                    product_record = ET.SubElement(root_data, "record", id = "product_product_"+str(product_count)+"_product_template", model="product.template")
                    ET.SubElement(product_record, "field", name="id").text = str(product['id'])
                    ET.SubElement(product_record, "field", name="name").text = product['title']
                    ET.SubElement(product_record, "field", name="public_categ_ids", eval="[(6,0,[ref('product_category_"+col['handle']+"')])]")
                    ET.SubElement(product_record, "field", name="list_price").text = product['variants'][0]['price']
                    ET.SubElement(product_record, "field", name="standard_price").text = product['variants'][0]['price']
                    ET.SubElement(product_record, "field", name="website_description").append(CDATA(validate_des(product['description'])))
                    ET.SubElement(product_record, "field", name="uom_id", ref="uom.product_uom_unit")
                    ET.SubElement(product_record, "field", name="uom_po_id", ref="uom.product_uom_unit")
                    ET.SubElement(product_record, "field", name="is_published", eval="True")

                    # export option to xml
                    option_count = 1
                    for option in product['options']:
                        print("processing file export ..")
                        option_record = ET.SubElement(root_data, "record", id = "product_"+str(product_count)+"_attribute_"+str(option_count)+"_product_template_attribute_line", model="product.template.attribute.line")
                        ET.SubElement(option_record, "field", name="product_tmpl_id", ref="product_product_"+str(product_count)+"_product_template")
                        ET.SubElement(option_record, "field", name="attribute_id", ref="product_attribute_"+option['name'].lower())
                        attribute_value = "[(6, 0, ["
                        i = 1
                        for value in option['values']:
                            attribute_value += "ref('"+ folder_name +".product_attribute_value_"+ option['name'].lower() +"_"+validate_variant_name(value)+"')"
                            if i < len(option['values']):
                                attribute_value += ", "
                                i+=1
                        attribute_value += "])]"
                        ET.SubElement(option_record, "field", name="value_ids", eval=attribute_value)
                        option_count += 1

                    # export function 1 to xml
                    function_1_record = ET.SubElement(root_data, "function", model="ir.model.data", name="_update_xmlids")
                    function_1_values = "["
                    option_count = 1
                    for option in product['options']:
                        print("processing file export  .")
                        i = 1
                        for value in option['values']:
                            function_1_values += "{'xml_id': '"+ folder_name +".product_" + str(product_count) + "_attribute_"+str(option_count)+"_value_"+str(i)+"',"
                            function_1_values += "'record': obj().env.ref('"+ folder_name +".product_"+ str(product_count) + "_attribute_"+str(option_count)+"_product_template_attribute_line').product_template_value_ids["+str(i-1)+"],'noupdate': True,},"
                            i+=1
                        option_count += 1
                    function_1_values += "]"
                    ET.SubElement(function_1_record, "value", model="base", eval=function_1_values)

                    # export function 2 to xml
                    function_2_record = ET.SubElement(root_data, "function", model="ir.model.data", name="_update_xmlids")
                    function_2_values = "["
                    option_count = 1
                    variant_count = 1
                    if len(product['options']) > 1:
                        if len(product['options']) == 2:
                            i_0 = 1
                            for value in product['options'][0]['values']:
                                print("processing file export. .")
                                i_1 = 1
                                for value2 in product['options'][1]['values']:
                                    function_2_values += "{'xml_id': '"+ folder_name +".product_product_" + str(product_count)+"_"+str(variant_count)+"',"
                                    function_2_values += "'record': obj().env.ref('"+ folder_name +".product_product_"+ str(product_count) +"_product_template')._get_variant_for_combination(obj().env.ref('"+ folder_name +".product_"+ str(product_count) +"_attribute_1_value_"+str(i_0)+"')"
                                    function_2_values += "+ obj().env.ref('"+ folder_name +".product_"+ str(product_count) +"_attribute_2_value_"+str(i_1)+"')"
                                    function_2_values += "),'noupdate': True,},"
                                    variant_count += 1
                                    i_1+=1
                                i_0+=1
                            function_2_values += "]"
                            ET.SubElement(function_2_record, "value", model="base", eval=function_2_values)
                        elif len(product['options']) == 3:
                            i_0 = 1
                            for value in product['options'][0]['values']:
                                i_1 = 1
                                for value2 in product['options'][1]['values']:
                                    i_2 = 1
                                    for value2 in product['options'][2]['values']:
                                        print("processing file export . ")
                                        function_2_values += "{'xml_id': '"+ folder_name +".product_product_" + str(product_count)+"_"+str(variant_count)+"',"
                                        function_2_values += "'record': obj().env.ref('"+ folder_name +".product_product_"+ str(product_count) +"_product_template')._get_variant_for_combination("
                                        function_2_values += "obj().env.ref('"+ folder_name +".product_"+ str(product_count) +"_attribute_1_value_"+str(i_0)+"')"
                                        function_2_values += "+ obj().env.ref('"+ folder_name +".product_"+ str(product_count) +"_attribute_2_value_"+str(i_1)+"')"
                                        function_2_values += "+ obj().env.ref('"+ folder_name +".product_"+ str(product_count) +"_attribute_3_value_"+str(i_2)+"')"
                                        function_2_values += "),'noupdate': True,},"
                                        variant_count += 1
                                        i_2+=1
                                    i_1+=1
                                i_0+=1
                            function_2_values += "]"
                            ET.SubElement(function_2_record, "value", model="base", eval=function_2_values)
                    else:
                        i = 1
                        for value in option['values']:
                            print("processing file export.  ")
                            function_2_values += "{'xml_id': '"+ folder_name +".product_product_" + str(product_count)+"_"+str(variant_count)+"',"
                            function_2_values += "'record': obj().env.ref('"+ folder_name +".product_product_"+ str(product_count) +"_product_template')._get_variant_for_combination(obj().env.ref('"+ folder_name +".product_"+ str(product_count) +"_attribute_1_value_"+str(i)+"')"
                            function_2_values += "),'noupdate': True,},"
                            variant_count += 1
                            i+=1
                        function_2_values += "]"
                        ET.SubElement(function_2_record, "value", model="base", eval=function_2_values)
                else:
                    print("processing file export  .")
                    product_record = ET.SubElement(root_data, "record", id = "product_product_"+str(product_count), model="product.product")
                    ET.SubElement(product_record, "field", name="id").text = str(product['id'])
                    ET.SubElement(product_record, "field", name="name").text = product['title']
                    ET.SubElement(product_record, "field", name="public_categ_ids", eval="[(6,0,[ref('product_category_"+col['handle']+"')])]")
                    ET.SubElement(product_record, "field", name="standard_price").text = product['variants'][0]['price']
                    img = ''
                    if product['images']:
                        if product['images'][0]['src']:
                            img = crawl_image(product['images'][0]['src'], folder_name)
                    if not product['variants'][0]['sku']:
                            product['variants'][0]['sku'] = str(product['variants'][0]['id'])
                    ET.SubElement(product_record, "field", name="default_code").text = product['variants'][0]['sku']
                    if not img == '':
                        ET.SubElement(product_record, "field", name="image_1920", type="base64", file=img)
                    ET.SubElement(product_record, "field", name="website_description").append(CDATA(validate_des(product['description'])))
                    ET.SubElement(product_record, "field", name="uom_id", ref="uom.product_uom_unit")
                    ET.SubElement(product_record, "field", name="uom_po_id", ref="uom.product_uom_unit")
                    ET.SubElement(product_record, "field", name="is_published", eval="True")
                    variant_check = False
                # export variant to xml
                if variant_check:
                    variant_count=1
                    for variant in product['variants']:
                        print("processing file export ..")
                        if not variant['sku']:
                            variant['sku'] = str(variant['id'])
                        img = ''
                        if variant['featured_image']:
                            if variant['featured_image']['src']:
                                img = crawl_image(variant['featured_image']['src'], folder_name)
                        variant_record = ET.SubElement(root_data, "record", id = "product_product_"+str(product_count)+"_"+str(variant_count), model="product.product")
                        ET.SubElement(variant_record, "field", name="default_code").text = variant['sku']
                        ET.SubElement(variant_record, "field", name="standard_price").text = variant['price']
                        if not img == '':
                            ET.SubElement(variant_record, "field", name="image_1920", type="base64", file=img)
                        variant_count+=1
                product_count += 1
            collection_count+=1
        tree = ET.ElementTree(root)
        tree.write(f, encoding='utf-8')

def format_xml(path):
    etree.parse(path).write(path, encoding="utf-8",pretty_print=True, xml_declaration = True)

def attribute_value_type(value):
    try:
        if int(value):
            rs = "int"
    except:
        rs="string"
    return rs


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--list-collections", dest="list_collections",
                    action="store_true",
                    help="List collections in the site")
    parser.add_option("--collections", "-c", dest="collections",
                    default="",
                    help="Download products only from the given collections (comma separated)")
    (options, args) = parser.parse_args()
    if len(args) > 1:
        demo_name = "demo.xml"
        folder_name = args[0]
        create_folder(folder_name, demo_name)
        url = fix_url(args[1])
        if not folder_name == '':
            if options.list_collections:
                for col in get_page_collections(url):
                    print(col['handle'])
            else:
                collections = []
                if options.collections:
                    collections = options.collections.split(',')
                extract_products(url, folder_name, demo_name, collections)
                format_xml(folder_name+"/data/"+demo_name)
                print("\nCOMPLETED!!!")