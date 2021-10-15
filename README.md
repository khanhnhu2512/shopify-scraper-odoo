# Overview

Shopify Scraper Odoo is a tool that functions to collect data - the data needed, such as finding data from photos, prices, names and others and push it into Odoo sample data

# Requirement

- Python 3, pip
- Some python module:
    - lxml  
    `pip install --upgrade lxml`
    - matplotlib  
    `pip install --upgrade matplotlib`
    
#  Usage

Run scraper by using the command below in the root directory:  
`python3 crawler.py odoosuite_sample_data https://example.myshopify.com/`  
Inside  
- `odoosuite_sample_data` is the root directory name and the module name, which is defined in the `__manifest__.py` file like that:  
`'name': 'Odoosuite Sample Data'`
- `https://example.myshopify.com/` is the website link you need to crawler