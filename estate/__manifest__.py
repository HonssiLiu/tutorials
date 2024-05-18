# -*- coding: utf-8 -*-
{
    'name': 'Real Estate',
    'version': '1.0',
    'category': 'Tutorials',
    'sequence': 1,
    'summary': 'Tutorials: Real Estate test',
    'depends': ['base'],
    'application': True,
    'data': [
        'security/ir.model.access.csv',

        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
    'license': 'AGPL-3'

}
