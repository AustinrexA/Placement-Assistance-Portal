"""Official career entry points for the 25 companies in the V4Career scope.

These are official career-page entry points from the project's scope sheet.
Catalog presence does not imply a live vacancy feed or successful extraction.
The structured collector only saves validated schema.org JobPosting records
that indicate an India location and stay on allowlisted official hosts.
"""
COMPANY_CAREER_SOURCES = [
    {'name': 'TCS Careers', 'company': 'TCS', 'base_url': 'https://www.tcs.com/careers/india', 'key': 'TCS', 'allowed_hosts': ['www.tcs.com'], 'discovery_urls': ['https://www.tcs.com/careers/india'], 'verified_collector': False},
    {'name': 'Infosys Careers', 'company': 'Infosys', 'base_url': 'https://career.infosys.com/jobs?countrycode=IN', 'key': 'INFOSYS', 'allowed_hosts': ['career.infosys.com'], 'discovery_urls': ['https://career.infosys.com/joblist?companyhiringtype=&countrycode=IN'], 'verified_collector': True},
    {'name': 'Accenture Careers', 'company': 'Accenture', 'base_url': 'https://www.accenture.com/in-en/careers', 'key': 'ACCENTURE', 'allowed_hosts': ['www.accenture.com', 'accenture.com'], 'discovery_urls': ['https://www.accenture.com/in-en/careers'], 'verified_collector': True},
    {'name': 'Cognizant Careers', 'company': 'Cognizant', 'base_url': 'https://careers.cognizant.com/india-en/', 'key': 'COGNIZANT', 'allowed_hosts': ['careers.cognizant.com'], 'discovery_urls': ['https://careers.cognizant.com/india-en/'], 'verified_collector': False},
    {'name': 'HCLTech Careers', 'company': 'HCLTech', 'base_url': 'https://www.hcltech.com/careers/careers-in-india', 'key': 'HCLTECH', 'allowed_hosts': ['www.hcltech.com', 'hcltech.com'], 'discovery_urls': ['https://www.hcltech.com/careers/careers-in-india'], 'verified_collector': True},
    {'name': 'Wipro Careers', 'company': 'Wipro', 'base_url': 'https://careers.wipro.com/', 'key': 'WIPRO', 'allowed_hosts': ['careers.wipro.com'], 'discovery_urls': ['https://careers.wipro.com/'], 'verified_collector': True},
    {'name': 'Capgemini Careers', 'company': 'Capgemini', 'base_url': 'https://www.capgemini.com/in-en/careers/', 'key': 'CAPGEMINI', 'allowed_hosts': ['www.capgemini.com', 'capgemini.com'], 'discovery_urls': ['https://www.capgemini.com/in-en/careers/'], 'verified_collector': False},
    {'name': 'Amazon Jobs', 'company': 'Amazon', 'base_url': 'https://www.amazon.jobs/en/search?country=IND&loc_query=India', 'key': 'AMAZON', 'allowed_hosts': ['www.amazon.jobs', 'amazon.jobs'], 'discovery_urls': ['https://www.amazon.jobs/en/search?country=IND&loc_query=India'], 'verified_collector': True},
    {'name': 'Deloitte India Careers', 'company': 'Deloitte', 'base_url': 'https://southasiacareers.deloitte.com/', 'key': 'DELOITTE', 'allowed_hosts': ['southasiacareers.deloitte.com'], 'discovery_urls': ['https://southasiacareers.deloitte.com/'], 'verified_collector': True},
    {'name': 'Tech Mahindra Careers', 'company': 'Tech Mahindra', 'base_url': 'https://www.techmahindra.com/en-in/careers/', 'key': 'TECH_MAHINDRA', 'allowed_hosts': ['www.techmahindra.com', 'techmahindra.com'], 'discovery_urls': ['https://www.techmahindra.com/en-in/careers/'], 'verified_collector': False},
    {'name': 'LTIMindtree Careers', 'company': 'LTIMindtree', 'base_url': 'https://www.ltm.com/india-careers', 'key': 'LTIMINDTREE', 'allowed_hosts': ['www.ltm.com'], 'discovery_urls': ['https://www.ltm.com/india-careers'], 'verified_collector': False},
    {'name': 'IBM Careers', 'company': 'IBM', 'base_url': 'https://www.ibm.com/careers/search', 'key': 'IBM', 'allowed_hosts': ['www.ibm.com', 'ibm.com'], 'discovery_urls': ['https://www.ibm.com/careers/search'], 'verified_collector': False},
    {'name': 'Oracle Careers', 'company': 'Oracle', 'base_url': 'https://www.oracle.com/in/careers/', 'key': 'ORACLE', 'allowed_hosts': ['www.oracle.com'], 'discovery_urls': ['https://www.oracle.com/in/careers/'], 'verified_collector': False},
    {'name': 'Zoho Careers', 'company': 'Zoho', 'base_url': 'https://www.zoho.com/careers/', 'key': 'ZOHO', 'allowed_hosts': ['www.zoho.com'], 'discovery_urls': ['https://www.zoho.com/careers/'], 'verified_collector': False},
    {'name': 'Mphasis Careers', 'company': 'Mphasis', 'base_url': 'https://careers.mphasis.com/', 'key': 'MPHASIS', 'allowed_hosts': ['careers.mphasis.com'], 'discovery_urls': ['https://careers.mphasis.com/'], 'verified_collector': False},
    {'name': 'Hexaware Careers', 'company': 'Hexaware', 'base_url': 'https://hexaware.com/careers/', 'key': 'HEXAWARE', 'allowed_hosts': ['hexaware.com'], 'discovery_urls': ['https://hexaware.com/careers/'], 'verified_collector': False},
    {'name': 'Persistent Systems Careers', 'company': 'Persistent Systems', 'base_url': 'https://www.persistent.com/careers/', 'key': 'PERSISTENT_SYSTEMS', 'allowed_hosts': ['www.persistent.com'], 'discovery_urls': ['https://www.persistent.com/careers/'], 'verified_collector': False},
    {'name': 'Microsoft Careers', 'company': 'Microsoft', 'base_url': 'https://careers.microsoft.com/', 'key': 'MICROSOFT', 'allowed_hosts': ['careers.microsoft.com'], 'discovery_urls': ['https://careers.microsoft.com/'], 'verified_collector': False},
    {'name': 'Google Careers', 'company': 'Google', 'base_url': 'https://www.google.com/about/careers/applications/', 'key': 'GOOGLE', 'allowed_hosts': ['www.google.com'], 'discovery_urls': ['https://www.google.com/about/careers/applications/'], 'verified_collector': False},
    {'name': 'CGI Careers', 'company': 'CGI', 'base_url': 'https://www.cgi.com/en/careers', 'key': 'CGI', 'allowed_hosts': ['www.cgi.com'], 'discovery_urls': ['https://www.cgi.com/en/careers'], 'verified_collector': False},
    {'name': 'Freshworks Careers', 'company': 'Freshworks', 'base_url': 'https://www.freshworks.com/company/careers/', 'key': 'FRESHWORKS', 'allowed_hosts': ['www.freshworks.com'], 'discovery_urls': ['https://www.freshworks.com/company/careers/'], 'verified_collector': False},
    {'name': 'Cisco Careers', 'company': 'Cisco', 'base_url': 'https://careers.cisco.com/global/en/india', 'key': 'CISCO', 'allowed_hosts': ['careers.cisco.com'], 'discovery_urls': ['https://careers.cisco.com/global/en/india'], 'verified_collector': False},
    {'name': 'Adobe Careers', 'company': 'Adobe', 'base_url': 'https://careers.adobe.com/', 'key': 'ADOBE', 'allowed_hosts': ['careers.adobe.com'], 'discovery_urls': ['https://careers.adobe.com/'], 'verified_collector': False},
    {'name': 'Qualcomm Careers', 'company': 'Qualcomm', 'base_url': 'https://careers.qualcomm.com/', 'key': 'QUALCOMM', 'allowed_hosts': ['careers.qualcomm.com'], 'discovery_urls': ['https://careers.qualcomm.com/'], 'verified_collector': False},
    {'name': 'NVIDIA Careers', 'company': 'NVIDIA', 'base_url': 'https://www.nvidia.com/en-us/about-nvidia/careers/', 'key': 'NVIDIA', 'allowed_hosts': ['www.nvidia.com'], 'discovery_urls': ['https://www.nvidia.com/en-us/about-nvidia/careers/'], 'verified_collector': False},
]

COMPANY_CAREER_BY_KEY = {item["key"]: item for item in COMPANY_CAREER_SOURCES}
COMPANY_CAREER_BY_NAME = {item["name"].casefold(): item for item in COMPANY_CAREER_SOURCES}
COMPANY_CAREER_BY_COMPANY = {item["company"].casefold(): item for item in COMPANY_CAREER_SOURCES}
