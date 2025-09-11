#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script transforms a JSON data file by normalizing the 'target_market' field
and inferring the 'business_model' for each use case.

Usage:
    python transform_data.py <input_file.json>
"""

import json
import sys
from typing import Any, Dict, List, Set

# RULE 1: CONSOLIDATION MAP
# A map to consolidate various target market names into a canonical form.
# The key is the original name, and the value is the canonical name.
# A value of "DELETE" means the market should be removed.
CONSOLIDATION_MAP: Dict[str, str] = {
    "Devops Engineers": "DevOps Teams & Engineers", "Devops Teams": "DevOps Teams & Engineers",
    "Front Desk Staff": "Hotel Managers & Staff", "Hotel Managers": "Hotel Managers & Staff",
    "Healthcare Admins": "Admins & Management", "It Managers": "Admins & Management", "Medical Administrators": "Admins & Management",
    "University Labs": "Research Labs", "Research Labs": "Research Labs",
    "Fitness Apps": "Fitness Enthusiasts", "Individuals With Sleep Issues": "Individuals With Disorders",
    "Angellist Competitors": "DELETE", "Gusto": "DELETE", "Rippling Competitors)": "DELETE",
    "Investors": "Angel Investors", "Cisos": "Compliance Officers",
    "Enterprise Sales Teams": "Sales Teams", "Legal Ops": "Legal Departments", "Saas Companies With High Arr": "Tech Startups",
    "Yc/Techstars Startups": "Tech Startups", "Cros At $50M+ Arr Saas Companies": "Large Companies",
    "Gyms": "Fitness Centers", "Personal Training Facilities": "Fitness Centers", "Sports Centers": "Fitness Centers", "Fitness Studios": "Fitness Centers",
    "Nonprofits": "Non-Profits & Charities", "Charities": "Non-Profits & Charities", "Saas Devs": "Software Developers", "Freelance Devs": "Software Developers", "Developers": "Software Developers",
    "Saas Founders": "Startup Founders", "Bootstrapped Saas Founders": "Startup Founders", "Indie Makers": "Indie Hackers", "Indie Hackers Building Niche Tools": "Indie Hackers",
    "E-Commerce Marketers": "Marketers", "Dtc Brands": "E-Commerce Brands", "D2C Brands": "E-Commerce Brands",
    "Clinics": "Healthcare Providers", "Private Practitioners": "Healthcare Providers", "Quant Teams": "Quantitative Traders & Developers", "Algo Developers": "Quantitative Traders & Developers", "Indie Quant Developers": "Quantitative Traders & Developers", "Quant Hobbyists": "Quantitative Traders & Developers", "Prop Firm Candidates": "Quantitative Traders & Developers",
    "Parents Of Neurodivergent Kids": "Family & Child Services", "Child Therapists": "Family & Child Services",
    "Overwhelmed Knowledge Workers": "General Consumers", "Indebted Consumers": "General Consumers", "Investing Enthusiasts": "General Consumers", "Consumers": "General Consumers",
    "Hr Tools (E.G.": "HR Teams", "Large Construction Companies": "Construction Companies", "Large Tech Companies": "Large Companies",
    "Mid-To-Large Enterprises": "Large Companies", "Enterprise Companies": "Large Companies", "Enterprises": "Large Companies",
    "Performance Marketing Agencies": "Marketing Agencies", "Investment Groups": "Investment Firms", "Investment Funds": "Investment Firms",
    "Small Businesses": "Small Business Owners", "Smbs": "Small Business Owners", "Smb Owners": "Small Business Owners", "Business Owners": "Small Business Owners",
    "Security Teams": "IT Security Departments", "Research Scientists": "Academic Researchers", "Academics": "Academic Researchers",
    "Self-Published Authors": "Authors", "E-Commerce Store Owners": "E-Commerce Owners & Managers", "Shopify Store Owners": "E-Commerce Owners & Managers",
    "Amazon Sellers": "E-Commerce Owners & Managers", "Retail Investors": "Retail Crypto Investors", "Retail Crypto Traders": "Retail Crypto Investors",
    "Traders": "Retail Crypto Investors", "Dental Startups": "Dental Practices", "Dental Offices": "Dental Practices",
    "Small Dental Practices": "Dental Practices", "Governments": "Government Agencies", "Healthcare Clinics": "Healthcare Providers",
    "Home Healthcare Agencies": "Healthcare Providers", "Hospitals": "Healthcare Providers", "Specialty Clinics": "Healthcare Providers",
    "Healthcare Systems": "Healthcare Providers", "Insurers": "Insurance Providers", "Logistics Providers": "Logistics Companies",
    "Manufacturing Plants": "Manufacturers", "SaaS Companies": "Tech Startups", "Software Companies": "Tech Companies",
    "Tech Enterprises": "Tech Companies", "University Law Schools": "Law Schools", "Expert Creators": "Content Creators",
    "Online Educators": "Educators", "Travel Managers": "Travel Agents", "University Students": "Students", "Payroll SaaS": "Tech Startups",
    "Backend Developers": "Software Developers", "Content Marketers": "Marketers", "Corporate Hr Teams": "HR Teams",
    "Corporate Legal Teams": "Legal Departments", "Corporate Travel Managers": "Travel Agents", "Crypto Analysts": "Analysts",
    "Finance Managers": "Financial Analysts", "High-Earning Freelancers": "Freelancers", "Hr Managers": "HR Teams",
    "Hygienists": "Healthcare Providers", "Indie Consultants": "Independent Consultants", "Indie Podcasters": "Content Creators",
    "Investment Analysts": "Financial Analysts", "Legal Ops Teams": "Legal Departments", "Legal Professionals": "Lawyers",
    "Level Designers": "Game Developers", "Mobile Engineers": "Software Developers", "Newsletter Writers": "Writers",
    "Non-Fiction Writers": "Authors", "Operations Managers": "Operations Teams", "Personal Finance Bloggers": "Bloggers",
    "Professional Editors": "Editors", "Revenue Operations": "Operations Teams", "Safety Inspectors": "Site Safety Officers",
    "Sales Development Representatives": "Sales Professionals", "Sales Managers": "Sales Teams", "Security Officers": "Site Safety Officers",
    "Self-Publishers": "Authors", "Seo Specialists": "Marketers", "Small Development Teams": "Engineering Teams",
    "Solopreneurs": "Small Business Owners", "Streamers": "Content Creators", "Therapists": "Healthcare Providers",
    "Video Creators": "Content Creators", "Vp Product At Plg Companies": "Product Managers", "Web3 Founders": "Startup Founders",
    "Writing Coaches": "Writers", "Youtubers": "Content Creators", "Creators": "Content Creators", "Consultants": "Independent Consultants",
    "Accelerators": "Tech Startups", "Advanced Retail": "Retail Stores", "Alt Lenders": "Lending Platforms",
    "B2B Companies": "Large Companies", "Bed & Breakfasts": "Small Inns", "Blockchain Startups": "Web3 Companies",
    "Bnpl Lenders": "Lending Platforms", "Chemical Distributors": "Chemical Companies", "Chemical Manufacturers": "Chemical Companies",
    "Conference Organizers": "Event Organizers", "Conservation Ngos": "Non-Profits & Charities", "Construction Firms": "Construction Companies",
    "Content Agencies": "Agencies", "Corporate Wellness Providers": "Wellness Coaches", "Creative Agencies": "Agencies",
    "E-Commerce Stores": "E-Commerce Brands", "Eco-Conscious Brands": "B-Corps", "Event Production Companies": "Event Producers",
    "Experiential Agencies": "Agencies", "Financial Firms": "Financial Services", "Fintech": "Fintech Companies",
    "Fintech Apps": "Fintech Companies", "Fintech Startups": "Fintech Companies", "Global Brands": "Large Companies",
    "Growing Startups": "Tech Startups", "Healthcare Tech": "Healthcare Providers", "Healthcare/Fintech Hr Teams": "HR Teams",
    "Hedge Funds": "Investment Firms", "Law Firms": "Legal Firms", "Local Restaurants": "Restaurants",
    "Meal Delivery Services": "Restaurants", "Prop Firms": "Investment Firms", "Regulated Enterprise Marketing Teams": "Marketing Teams",
    "Retailers": "Retail Stores", "Shopify Stores": "E-Commerce Brands", "Small Law Firms": "Legal Firms",
    "Small Retailers": "Small Businesses", "Small Teams": "Tech Startups", "Smbs With Trademarks": "Small Businesses",
    "Startup Teams": "Tech Startups", "Startups": "Tech Startups", "Back-Office Teams": "Operations Teams",
    "Factory Floor Managers": "Manufacturing", "Finance Teams": "Finance Departments", "Legal Teams": "Legal Departments",
    "Remote Teams": "Remote Companies", "Sre Teams": "Engineering Teams", "Airbnb Hosts With 5+ Properties": "Small Landlords",
    "Bargain Hunters": "General Consumers", "Crypto Discord Communities": "DeFi Users", "Health-Conscious Individuals": "Wellness-Conscious Consumers",
    "Online Shoppers": "General Consumers", "Small Remote Teams": "Remote Companies", "Web3 Users": "DeFi Users",
    "Indie Hackers Building Regulated Micro-Saas": "Indie Hackers", "Staking Operators": "Web3 Companies",
    "Staking Services": "Web3 Companies", "Blockchain Validators": "Web3 Companies", "Wellness Providers": "Wellness Coaches",
    "Blockchain Developers": "Web3 Developers", "City Planners": "City Planners", "Cpg Companies": "CPG Companies",
    "Crypto Investors": "Retail Crypto Investors", "Crypto Traders": "Retail Crypto Investors", "Ctos": "CTOs",
    "Customer Support Teams": "Support Teams", "Daos": "Crypto Projects", "Defi Projects": "Crypto Projects",
    "Defi Users": "DeFi Users", "Dental Practices": "Dental Practices", "Development Agencies": "Development Agencies",
    "E-Commerce Managers": "E-Commerce Owners & Managers", "Enterprise Compliance Officers": "Compliance Officers",
    "Enterprise It Departments": "IT Departments", "Event Planners": "Event Organizers", "Fiction Authors": "Authors",
    "Fintech Companies": "Fintech Companies", "Freelance Travel Agents": "Travel Agents", "Gym Owners": "Gym Owners",
    "Hr Departments": "HR Departments", "Hr Teams": "HR Teams", "Indie Developers": "Indie Hackers",
    "Individuals": "General Consumers", "It Departments": "IT Departments",
    "Maintenance Repair Organizations (Mros)": "Maintenance & Repair Organizations (MROs)",
    "Managed Service Providers (Msps)": "Managed Service Providers (MSPs)",
    "Marketing Departments": "Marketing Teams", "Marketing Teams": "Marketing Teams", "Non-Profits": "Non-Profits & Charities",
    "Orthodontists": "Dental Practices", "Podcasters": "Content Creators", "Preschool Educators": "Educators",
    "Remote Companies": "Tech Startups", # Updated per map logic
    "Research Teams": "Researchers", "Retail Traders": "Retail Crypto Investors",
    "Small Landlords (1-10 Units)": "Small Landlords", "Solo Gps": "Solo General Partners (GPs)",
    "Specialty Clinics With 5-20 Providers": "Healthcare Providers", "Startup Ctos": "CTOs",
    "Trading Communities": "Quantitative Traders & Developers", "Ui/Ux Designers": "UI/UX Designers",
    "University Researchers": "Academic Researchers", "Ux Designers": "UI/UX Designers", "Ux Researchers": "UX Researchers",
    "Vc-Backed Startups": "Tech Startups", "Vcs": "VCs",
    "Aestheticians": "Skincare Professionals", "Ai Ethics Teams": "Compliance Teams", "Ai Researchers": "Academic Researchers",
    "Ai Startups Handling Pii": "Tech Startups", "Backend Engineers": "Software Developers",
    "Barbershops": "Hair Salons and Barbershops", "Billing Departments": "Finance Departments",
    "Booking Platforms": "Tech Startups", "Corporations": "Large Companies", "Devops": "DevOps Teams & Engineers",
    "Engineering Managers": "Team Managers", "Facility Managers": "Facilities Managers", "Growth Teams": "Marketing Teams",
    "Health Insurers": "Insurance Providers", "Independent Stylists": "Freelancers",
    "Local Businesses With Hourly Workers": "Small Businesses", "Logistics": "Logistics Companies",
    "Online Retailers": "E-Commerce Brands", "Promo-Seeking Tech Workers": "General Consumers",
    "Remote Developers": "Software Developers", "Series B+ Fintech Companies": "Fintech Companies",
    "Shopify/Wix Agencies": "Agencies", "Skincare Brands": "E-Commerce Brands", "Small Agencies": "Agencies",
    "Hair Salons": "Hair Salons & Barbershops", "Small Business Owners": "Small Businesses",
    "Small Dev Teams": "Engineering Teams", "Subscription Box Businesses": "E-Commerce Brands",
    "Sustainability Consultants": "Independent Consultants", "Team Leads": "Team Managers",
    "Training Coordinators": "HR Teams", "Travel Agencies": "Travel Agents & Agencies",
    "Travel Agents": "Travel Agents & Agencies", "Boutique Travel Agencies": "Travel Agents & Agencies",
    "Web3 Analysts": "Analysts", "Web3 Startups": "Web3 Companies", "Web3/Ai Startups Hiring Specialists": "HR Teams",
    "Hair Salons & Barbershops": "Hair Salons and Barbershops", "digital banks": "Neobanks", "Enterprise teams": "Large Companies", "High-net-worth individuals" :"High-Net-Worth Individuals", "Financial advisors" : "Advisors", "gaming platforms": "Gaming Companies", "independent contractors": "Freelancers", "edtech companies": "E-Learning Platforms", "crypto exchanges" : "Web3 Companies", "social media platforms" : "Media Companies", "freelancers" : "Freelancers", "recruiters": "Recruiters", "Affiliate marketers" : "Marketers", "Advertisers": "Marketers", "Marketing agencies": "Marketing Agencies", "Content creators": "Content Creators", "PPC specialists": "Marketers", "Job seekers": "Job Seekers", 
    "Hair Salons & Barbershops": "Hair Salons and Barbershops", "digital banks": "Neobanks", "Enterprise teams": "Large Companies", "High-net-worth individuals" :"High-Net-Worth Individuals", "Financial advisors" : "Advisors", "gaming platforms": "Gaming Companies", "independent contractors": "Freelancers", "edtech companies": "E-Learning Platforms", "crypto exchanges" : "Web3 Companies", "social media platforms" : "Media Companies", "freelancers" : "Freelancers", "recruiters": "Recruiters", "Affiliate marketers" : "Marketers", "Advertisers": "Marketers", "Marketing agencies": "Marketing Agencies", "Content creators": "Content Creators", "PPC specialists": "Marketers", "Job seekers": "Job Seekers", 
    "Hair Salons & Barbershops": "Hair Salons and Barbershops", "digital banks": "Neobanks", "Enterprise teams": "Large Companies", "Financial advisors" : "Advisors", "gaming platforms": "Gaming Companies", "independent contractors": "Freelancers", "edtech companies": "E-Learning Platforms", "crypto exchanges" : "Web3 Companies", "social media platforms" : "Media Companies", "freelancers" : "Freelancers", "recruiters": "Recruiters", "Affiliate marketers" : "Marketers", "Advertisers": "Marketers", "Marketing agencies": "Marketing Agencies", "Content creators": "Content Creators", "PPC specialists": "Marketers", "Job seekers": "Job Seekers", "Professionals": "Job Seekers", "Recent graduates": "Job Seekers", "Tech professionals": "Software Developers", "Enterprise teams": "Large Companies", "Sales professionals": "Sales Professionals"


}

# RULE 2: BUSINESS MODEL CLASSIFICATION SETS
B2B_SET: Set[str] = {"Accounting Firms", "Aerospace Manufacturers", "Agencies", "Agriculture Companies", "Airlines", "Banks", "B-Corps", "Biotech Startups", "Boutique Hotels", "Boutique Travel Agencies", "Chemical Companies", "Compliance Teams", "Construction Companies", "Construction Smbs", "Consulting Firms", "Corporate Event Planners", "CPG Companies", "Credit Repair Agencies", "Credit Unions", "Crypto Projects", "Defense Contractors", "Dental Practices", "Design Agencies", "Digital Agencies", "E-Commerce Brands", "E-Commerce Platforms", "E-Learning Platforms", "Engineering Teams", "Factories", "Finance Departments", "Financial Services", "Fintech Companies", "Fire Departments", "Fitness Centers", "Florists", "Forestry Services", "Freight Forwarders", "Government Agencies", "Hair Salons and Barbershops", "Healthcare Providers", "Hotel Managers & Staff", "HR Departments", "HR Teams", "Independent Bookstores", "Industrial Ops", "Insurance Providers", "Investment Firms", "IT Departments", "Recruiters", "IT Security Departments", "Junk Removal Services", "K-12 Teachers", "Labs", "Large Companies", "Law Schools", "Learning & Development Teams", "Legal Departments", "Legal Firms", "Lending Platforms", "Logistics Companies", "Managed Service Providers (MSPs)", "Manufacturers", "Manufacturing", "Marketing Agencies", "Marketing Teams", "Media Companies", "Moving Companies", "Municipal Governments", "Neobanks", "Non-Profits & Charities", "Operations Teams", "Paralegal Programs", "Product Teams", "Professional Certification Bodies", "Public Companies", "Publishers", "Real Estate Developers", "Rehabilitation Clinics", "Research Institutions", "Research Labs", "Restaurants", "Retail Stores", "Sales Teams", "School Districts", "Schools", "Smb Payroll Providers", "Small Inns", "Small Businesses", "Small Presses", "Staking Pools", "Support Teams", "Tech Companies", "Tech Startups", "Travel Agents & Agencies", "Universities", "Warehouses", "Web3 Companies", "Gaming Companies"}
PROSUMER_SET: Set[str] = {"Accountants", "Account Executives", "Academic Researchers", "Admins & Management", "Advisors", "Agency Owners", "Analysts", "Angel Investors", "Architects", "Athletes", "Audio Engineers", "Authors", "Bloggers", "Business Analysts", "Business Development Reps", "Caregivers", "Certification Candidates", "Chemical Engineers", "Coaches", "Community Builders", "Compliance Officers", "Content Creators", "Corporate Trainers", "Course Creators", "CTOs", "Data Analysts", "Data Engineers", "Data Scientists", "Demand Generation Managers", "Dermatology Clinics", "Design Studios", "DevOps Teams & Engineers", "Dietitians", "Digital Marketers", "Doctors", "E-Commerce Owners & Managers", "Editors", "Educators", "Environmental Agencies", "Event Organizers", "Event Producers", "Executives", "Financial Analysts", "Financial Coaches", "Freelancers", "Game Developers", "General Contractors", "Growth Marketers", "Illustrators", "Indie Game Studios", "Indie Hackers", "Independent Consultants", "Job Seekers", "Law Students", "Lawyers", "Librarians", "Market Researchers", "Marketers", "Nutritionists", "Paralegals", "Personal Trainers", "Physiotherapists", "Policymakers", "Product Managers", "Project Developers", "Project Managers", "Public Speakers", "Quantitative Traders & Developers", "Quality Assurance Teams", "Renewable Energy Investors", "Researchers", "Sales Professionals", "Security Engineers", "SEO Specialists", "Site Reliability Engineers", "Site Safety Officers", "Skincare Professionals", "Small Business Owners", "Small Contractors", "Small Landlords", "Social Media Managers", "Software Architects", "Software Developers", "Solo Attorneys", "Solo General Partners (GPs)", "Startup Founders", "Sustainability Officers", "System Administrators", "Team Managers", "Tradespeople", "UI/UX Designers", "UX Designers", "UX Researchers", "VCs", "Web3 Developers", "Webinar Hosts", "Wellness Coaches", "Writers"}
B2C_SET: Set[str] = {"Affluent Solo Travelers", "Airbnb Hosts", "Career-Switchers", "Children", "Couples", "DeFi Users", "Digital Nomads", "Expatriates", "Families", "Family & Child Services", "Fitness Enthusiasts", "Frequent Travelers", "Friends", "General Consumers", "High School Students", "Honeymooners", "Individuals With Disorders", "Language Learners", "New Parents", "Parents", "Retail Crypto Investors", "Small Travel Groups", "Students", "Wellness-Conscious Consumers"}


def normalize_target_markets(markets: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Normalizes a list of target market objects using the CONSOLIDATION_MAP.
    This version is robust against whitespace and case-sensitivity issues.
    """
    # Create a lowercased version of the map for case-insensitive lookups
    CONSOLIDATION_MAP_LOWER = {k.lower(): v for k, v in CONSOLIDATION_MAP.items()}
    
    canonical_names = set()
    for market in markets:
        original_name = market.get("name")
        if not original_name:
            continue
        
        # Clean the input: remove whitespace and make it lowercase for lookup
        clean_name = original_name.strip().lower()
        
        # Look up the cleaned name in the lowercased map.
        # If not found, default back to the original (but stripped) name.
        canonical_name = CONSOLIDATION_MAP_LOWER.get(clean_name, original_name.strip())
        
        if canonical_name != "DELETE":
            canonical_names.add(canonical_name)
            
    # Return a sorted list of dicts for consistent output
    return [{"name": name} for name in sorted(list(canonical_names))]


def infer_business_model(normalized_markets: List[Dict[str, str]]) -> str:
    """
    Infers the business model based on a prioritized list of normalized markets.
    Priority: B2B > Prosumer > B2C. Default: Prosumer.
    """
    market_names = {market["name"] for market in normalized_markets}
    
    # 1. Check for B2B
    # set.isdisjoint() is False if there is at least one common element
    if not B2B_SET.isdisjoint(market_names):
        return "B2B"
        
    # 2. Check for Prosumer
    if not PROSUMER_SET.isdisjoint(market_names):
        return "Prosumer"
        
    # 3. Check for B2C
    if not B2C_SET.isdisjoint(market_names):
        return "B2C"
        
    # 4. Default if no match is found
    return "Prosumer"

def transform_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies all transformation rules to the input data object.
    """
    if "use_cases" in data and isinstance(data["use_cases"], list):
        for use_case in data["use_cases"]:
            # Step 1: Normalize the target_market list
            original_markets = use_case.get("target_market", [])
            normalized_markets = normalize_target_markets(original_markets)
            use_case["target_market"] = normalized_markets
            
            # Step 2: Infer and add the business_model
            business_model = infer_business_model(normalized_markets)
            use_case["business_model"] = business_model
            
    return data

def main():
    """
    Main function to run the script.
    Handles command-line arguments, file I/O, and calls the transformation logic.
    """
    if len(sys.argv) != 2:
        print("Usage: python transform_data.py <input_file.json>", file=sys.stderr)
        sys.exit(1)
        
    input_filepath = sys.argv[1]
    input_data = None
    
    try:
        # First, try to open as standard UTF-8.
        with open(input_filepath, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except UnicodeDecodeError:
        # If UTF-8 fails, the file is likely UTF-16 with a BOM.
        print(f"Info: UTF-8 decoding failed. Retrying with UTF-16 for {input_filepath}...", file=sys.stderr)
        try:
            with open(input_filepath, 'r', encoding='utf-16') as f:
                input_data = json.load(f)
        except Exception as e:
            print(f"Error: Failed to read file with UTF-16 encoding. Details: {e}", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{input_filepath}'. Details: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if the loaded data is a list of objects or a single object
    if isinstance(input_data, list):
        # Process each object in the list
        processed_data = [transform_data(item) for item in input_data]
    elif isinstance(input_data, dict):
        # Process the single object
        processed_data = transform_data(input_data)
    else:
        print("Error: Input JSON must be an object or a list of objects.", file=sys.stderr)
        sys.exit(1)
    
    # Print the final JSON to standard output with beautiful formatting
    json.dump(processed_data, sys.stdout, indent=2)
    # Add a final newline for clean output in terminals
    print()


if __name__ == "__main__":
    main()