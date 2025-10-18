SELECT *
FROM (SELECT m.name,
             p.oem_part_number,
             MAX(CASE WHEN l.code = 'de' THEN pt.name END) AS de,
             MAX(CASE WHEN l.code = 'en' THEN pt.name END) AS en,
             MAX(CASE WHEN l.code = 'es' THEN pt.name END) AS es,
             MAX(CASE WHEN l.code = 'it' THEN pt.name END) AS it,
             MAX(CASE WHEN l.code = 'nl' THEN pt.name END) AS nl,
             MAX(CASE WHEN l.code = 'pt' THEN pt.name END) AS pt,
             MAX(CASE WHEN l.code = 'fr' THEN pt.name END) AS fr
      FROM products p
               LEFT JOIN product_translations pt ON p.id = pt.product_id
               LEFT JOIN wsu_ebusiness.languages l ON pt.language_id = l.id
               LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
      GROUP BY p.manufacturer_id, p.oem_part_number) t
WHERE de IS NULL
   OR en IS NULL
   OR es IS NULL
   OR it IS NULL
   OR nl IS NULL
   OR pt IS NULL
   OR fr IS NULL;




SELECT *
FROM (SELECT m.name,
             p.oem_part_number,
             MAX(CASE WHEN l.code = 'de' THEN pt.description END) AS de,
             MAX(CASE WHEN l.code = 'en' THEN pt.description END) AS en,
             MAX(CASE WHEN l.code = 'es' THEN pt.description END) AS es,
             MAX(CASE WHEN l.code = 'it' THEN pt.description END) AS it,
             MAX(CASE WHEN l.code = 'nl' THEN pt.description END) AS nl,
             MAX(CASE WHEN l.code = 'pt' THEN pt.description END) AS pt,
             MAX(CASE WHEN l.code = 'fr' THEN pt.description END) AS fr
      FROM products p
               LEFT JOIN product_translations pt ON p.id = pt.product_id
               LEFT JOIN wsu_ebusiness.languages l ON pt.language_id = l.id
               LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
      GROUP BY p.manufacturer_id, p.oem_part_number) t
WHERE de IS NULL
   OR en IS NULL
   OR es IS NULL
   OR it IS NULL
   OR nl IS NULL
   OR pt IS NULL
   OR fr IS NULL;





SELECT *
FROM (SELECT m.name,
             p.oem_part_number,
             MAX(CASE WHEN l.code = 'de' THEN pt.meta_title END) AS de,
             MAX(CASE WHEN l.code = 'en' THEN pt.meta_title END) AS en,
             MAX(CASE WHEN l.code = 'es' THEN pt.meta_title END) AS es,
             MAX(CASE WHEN l.code = 'it' THEN pt.meta_title END) AS it,
             MAX(CASE WHEN l.code = 'nl' THEN pt.meta_title END) AS nl,
             MAX(CASE WHEN l.code = 'pt' THEN pt.meta_title END) AS pt,
             MAX(CASE WHEN l.code = 'fr' THEN pt.meta_title END) AS fr
      FROM products p
               LEFT JOIN product_translations pt ON p.id = pt.product_id
               LEFT JOIN wsu_ebusiness.languages l ON pt.language_id = l.id
               LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
      GROUP BY p.manufacturer_id, p.oem_part_number) t
WHERE de IS NULL
   OR en IS NULL
   OR es IS NULL
   OR it IS NULL
   OR nl IS NULL
   OR pt IS NULL
   OR fr IS NULL;



SELECT *
FROM (SELECT m.name,
             p.oem_part_number,
             MAX(CASE WHEN l.code = 'de' THEN pt.meta_description END) AS de,
             MAX(CASE WHEN l.code = 'en' THEN pt.meta_description END) AS en,
             MAX(CASE WHEN l.code = 'es' THEN pt.meta_description END) AS es,
             MAX(CASE WHEN l.code = 'it' THEN pt.meta_description END) AS it,
             MAX(CASE WHEN l.code = 'nl' THEN pt.meta_description END) AS nl,
             MAX(CASE WHEN l.code = 'pt' THEN pt.meta_description END) AS pt,
             MAX(CASE WHEN l.code = 'fr' THEN pt.meta_description END) AS fr
      FROM products p
               LEFT JOIN product_translations pt ON p.id = pt.product_id
               LEFT JOIN wsu_ebusiness.languages l ON pt.language_id = l.id
               LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
      GROUP BY p.manufacturer_id, p.oem_part_number) t
WHERE de IS NULL
   OR en IS NULL
   OR es IS NULL
   OR it IS NULL
   OR nl IS NULL
   OR pt IS NULL
   OR fr IS NULL;



SELECT *
FROM (SELECT m.name,
             p.oem_part_number,
             MAX(CASE WHEN l.code = 'de' THEN pt.meta_keywords_json END) AS de,
             MAX(CASE WHEN l.code = 'en' THEN pt.meta_keywords_json END) AS en,
             MAX(CASE WHEN l.code = 'es' THEN pt.meta_keywords_json END) AS es,
             MAX(CASE WHEN l.code = 'it' THEN pt.meta_keywords_json END) AS it,
             MAX(CASE WHEN l.code = 'nl' THEN pt.meta_keywords_json END) AS nl,
             MAX(CASE WHEN l.code = 'pt' THEN pt.meta_keywords_json END) AS pt,
             MAX(CASE WHEN l.code = 'fr' THEN pt.meta_keywords_json END) AS fr
      FROM products p
               LEFT JOIN product_translations pt ON p.id = pt.product_id
               LEFT JOIN wsu_ebusiness.languages l ON pt.language_id = l.id
               LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
      GROUP BY p.manufacturer_id, p.oem_part_number) t
WHERE de IS NULL
   OR en IS NULL
   OR es IS NULL
   OR it IS NULL
   OR nl IS NULL
   OR pt IS NULL
   OR fr IS NULL;



SELECT *
FROM (SELECT m.name,
             p.oem_part_number,
             MAX(CASE WHEN l.code = 'de' THEN pt.search_keywords_json END) AS de,
             MAX(CASE WHEN l.code = 'en' THEN pt.search_keywords_json END) AS en,
             MAX(CASE WHEN l.code = 'es' THEN pt.search_keywords_json END) AS es,
             MAX(CASE WHEN l.code = 'it' THEN pt.search_keywords_json END) AS it,
             MAX(CASE WHEN l.code = 'nl' THEN pt.search_keywords_json END) AS nl,
             MAX(CASE WHEN l.code = 'pt' THEN pt.search_keywords_json END) AS pt,
             MAX(CASE WHEN l.code = 'fr' THEN pt.search_keywords_json END) AS fr
      FROM products p
               LEFT JOIN product_translations pt ON p.id = pt.product_id
               LEFT JOIN wsu_ebusiness.languages l ON pt.language_id = l.id
               LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
      GROUP BY p.manufacturer_id, p.oem_part_number) t
WHERE de IS NULL
   OR en IS NULL
   OR es IS NULL
   OR it IS NULL
   OR nl IS NULL
   OR pt IS NULL
   OR fr IS NULL;
