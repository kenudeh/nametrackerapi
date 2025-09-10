import json
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import TargetMarket, UseCase

class Command(BaseCommand):
    help = 'Final script to clean remaining TargetMarkets and backfill UseCase business_models.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Pre-Flight Check: Identifying all unmapped terms ---"))
        if not self.identify_unmapped_targets():
            return

        self.stdout.write(self.style.SUCCESS("\n--- Phase 1: Cleaning remaining TargetMarket data ---"))
        self.clean_target_markets()
        self.stdout.write(self.style.SUCCESS("\n--- Phase 2: Backfilling UseCase Business Models ---"))
        self.backfill_business_models()
        self.stdout.write(self.style.SUCCESS("\n✅ Final operation completed successfully!"))

    def get_approved_list(self):
        json_file = "api/fixtures/target_markets.json"
        with open(json_file) as f:
            return {item['name'] for item in json.load(f)}

    def get_consolidation_map(self):
        # This is the final, complete consolidation map including all revisions.
        return {
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
            # This is the big list from the last round
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
            #New additions
            "Blockchain Developers": "Web3 Developers",
            "City Planners": "City Planners", # Mapping to self to catch variations
            "Cpg Companies": "CPG Companies",
            "Crypto Investors": "Retail Crypto Investors",
            "Crypto Traders": "Retail Crypto Investors",
            "Ctos": "CTOs",
            "Customer Support Teams": "Support Teams",
            "Daos": "Crypto Projects",
            "Defi Projects": "Crypto Projects",
            "Defi Users": "DeFi Users",
            "Dental Practices": "Dental Practices", # Mapping to self
            "Development Agencies": "Development Agencies", # Mapping to self
            "E-Commerce Managers": "E-Commerce Owners & Managers",
            "Enterprise Compliance Officers": "Compliance Officers",
            "Enterprise It Departments": "IT Departments",
            "Event Planners": "Event Organizers",
            "Fiction Authors": "Authors",
            "Fintech Companies": "Fintech Companies", # Mapping to self
            "Freelance Travel Agents": "Travel Agents",
            "Gym Owners": "Gym Owners",
            "Hr Departments": "HR Departments",
            "Hr Teams": "HR Teams",
            "Indie Developers": "Indie Hackers",
            "Individuals": "General Consumers",
            "It Departments": "IT Departments",
            "Maintenance Repair Organizations (Mros)": "Maintenance & Repair Organizations (MROs)", # See note below
            "Managed Service Providers (Msps)": "Managed Service Providers (MSPs)",
            "Marketing Departments": "Marketing Teams",
            "Marketing Teams": "Marketing Teams", # Mapping to self
            "Non-Profits": "Non-Profits & Charities",
            "Orthodontists": "Dental Practices",
            "Podcasters": "Content Creators",
            "Preschool Educators": "Educators",
            "Remote Companies": "Remote Companies", # Mapping to self
            "Research Teams": "Researchers",
            "Retail Traders": "Retail Crypto Investors",
            "Small Landlords (1-10 Units)": "Small Landlords",
            "Solo Gps": "Solo Gps", # Mapping to self
            "Specialty Clinics With 5-20 Providers": "Healthcare Providers",
            "Startup Ctos": "CTOs",
            "Trading Communities": "Quantitative Traders & Developers",
            "Ui/Ux Designers": "UI/UX Designers",
            "University Researchers": "Academic Researchers",
            "Ux Designers": "UI/UX Designers",
            "Ux Researchers": "UX Researchers",
            "Vc-Backed Startups": "Tech Startups",
            "Vcs": "VCs",
            #Production data
            "Aestheticians": "Skincare Professionals",
            "Ai Ethics Teams": "Compliance Teams",
            "Ai Researchers": "Academic Researchers",
            "Ai Startups Handling Pii": "Tech Startups",
            "Backend Engineers": "Software Developers",
            "Barbershops": "Hair Salons and Barbershops",
            "Billing Departments": "Finance Departments",
            "Booking Platforms": "Tech Startups",
            "Corporations": "Large Companies",
            "Devops": "DevOps Teams & Engineers",
            "Engineering Managers": "Team Managers",
            "Facility Managers": "Facilities Managers", # Merging into the plural form
            "Growth Teams": "Marketing Teams",
            "Health Insurers": "Insurance Providers",
            "Independent Stylists": "Freelancers", # A type of freelancer
            "Local Businesses With Hourly Workers": "Small Businesses", # See note below
            "Logistics": "Logistics Companies",
            "Online Retailers": "E-Commerce Brands",
            "Promo-Seeking Tech Workers": "General Consumers",
            "Remote Developers": "Software Developers",
            "Series B+ Fintech Companies": "Fintech Companies",
            "Shopify/Wix Agencies": "Agencies",
            "Skincare Brands": "E-Commerce Brands",
            "Small Agencies": "Agencies",

            "Hair Salons": "Hair Salons & Barbershops",
            "Payroll Saas": "Tech Startups",
            "Saas Companies": "Tech Startups",
            "Small Business Owners": "Small Businesses",
            "Small Dev Teams": "Engineering Teams",
            "Subscription Box Businesses": "E-Commerce Brands",
            "Sustainability Consultants": "Independent Consultants",
            "Team Leads": "Team Managers",
            "Training Coordinators": "HR Teams",
            "Travel Agencies": "Travel Agents & Agencies", 
            "Boutique Travel Agencies": "Travel Agents & Agencies",
            "Web3 Analysts": "Analysts",
            "Web3 Startups": "Web3 Companies",
            "Web3/Ai Startups Hiring Specialists": "HR Teams",
        }

    def identify_unmapped_targets(self):
        approved_names = self.get_approved_list()
        consolidation_map = self.get_consolidation_map()
        all_db_names = set(TargetMarket.objects.values_list('name', flat=True))
        unmapped_names = {name for name in all_db_names if name not in approved_names and name not in consolidation_map}
        if unmapped_names:
            self.stdout.write(self.style.ERROR("Found unmapped TargetMarkets! Please add these to the consolidation_map and run again:"))
            for name in sorted(list(unmapped_names)): self.stdout.write(f"- '{name}'")
            return False
        self.stdout.write(self.style.SUCCESS("  ✅ All TargetMarkets are mapped. Proceeding..."))
        return True

    @transaction.atomic
    def clean_target_markets(self):
        consolidation_map = self.get_consolidation_map()
        for old_name, canonical_name in consolidation_map.items():
            if canonical_name == "DELETE":
                TargetMarket.objects.filter(name__iexact=old_name).delete()
                self.stdout.write(f"  Deleting '{old_name}'...")
                continue
            try:
                canonical_tm, _ = TargetMarket.objects.get_or_create(name=canonical_name)
                old_tms = TargetMarket.objects.filter(name__iexact=old_name).exclude(pk=canonical_tm.pk)
                if not old_tms.exists(): continue
                self.stdout.write(f"  Merging '{old_name}' into '{canonical_name}'...")
                use_cases_to_update = UseCase.objects.filter(target_markets__in=old_tms)
                for uc in use_cases_to_update.iterator():
                    uc.target_markets.remove(*old_tms)
                    uc.target_markets.add(canonical_tm)
                old_tms.delete()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  An error occurred while merging '{old_name}': {e}"))

    @transaction.atomic
    def backfill_business_models(self):
        # The classification sets are now derived directly from the master JSON
        B2B_SET = {"Accounting Firms", "Aerospace Manufacturers", "Agencies", "Agriculture Companies", "Airlines", "Banks", "B-Corps", "Biotech Startups", "Boutique Hotels", "Boutique Travel Agencies", "Chemical Companies", "Compliance Teams", "Construction Companies", "Construction Smbs", "Consulting Firms", "Corporate Event Planners", "CPG Companies", "Credit Repair Agencies", "Credit Unions", "Crypto Projects", "Defense Contractors", "Design Agencies", "Digital Agencies", "E-Commerce Brands", "E-Commerce Platforms", "E-Learning Platforms", "Engineering Teams", "Factories", "Finance Departments", "Financial Services", "Fire Departments", "Fitness Centers", "Florists", "Forestry Services", "Freight Forwarders", "Government Agencies", "Hair Salons and Barbershops", "Healthcare Providers", "Hotel Managers & Staff", "HR Departments", "HR Teams", "Independent Bookstores", "Industrial Ops", "Insurance Providers", "Investment Firms", "IT Departments", "IT Security Departments", "Junk Removal Services", "K-12 Teachers", "Labs", "Large Companies", "Law Schools", "Learning & Development Teams", "Legal Departments", "Legal Firms", "Lending Platforms", "Logistics Companies", "Managed Service Providers (MSPs)", "Manufacturers", "Manufacturing", "Marketing Agencies", "Media Companies", "Moving Companies", "Municipal Governments", "Neobanks", "Non-Profits & Charities", "Operations Teams", "Paralegal Programs", "Product Teams", "Professional Certification Bodies", "Public Companies", "Publishers", "Real Estate Developers", "Rehabilitation Clinics", "Research Institutions", "Research Labs", "Restaurants", "Retail Stores", "Sales Teams", "School Districts", "Schools", "Smb Payroll Providers", "Small Inns", "Small Presses", "Staking Pools", "Support Teams", "Tech Companies", "Tech Startups", "Universities", "Warehouses", "Web3 Companies"}
        PROSUMER_SET = {"Accountants", "Account Executives", "Academic Researchers", "Admins & Management", "Advisors", "Agency Owners", "Analysts", "Angel Investors", "Architects", "Athletes", "Audio Engineers", "Authors", "Bloggers", "Business Analysts", "Business Development Reps", "Caregivers", "Certification Candidates", "Chemical Engineers", "Coaches", "Community Builders", "Compliance Officers", "Content Creators", "Corporate Trainers", "Course Creators", "CTOs", "Data Analysts", "Data Engineers", "Data Scientists", "Demand Generation Managers", "Dermatology Clinics", "Design Studios", "DevOps Teams & Engineers", "Dietitians", "Digital Marketers", "Doctors", "E-Commerce Owners & Managers", "Editors", "Educators", "Environmental Agencies", "Event Organizers", "Event Producers", "Executives", "Financial Analysts", "Financial Coaches", "Freelancers", "Game Developers", "General Contractors", "Growth Marketers", "Illustrators", "Indie Game Studios", "Indie Hackers", "Independent Consultants", "Job Seekers", "Law Students", "Lawyers", "Librarians", "Market Researchers", "Marketers", "Nutritionists", "Paralegals", "Personal Trainers", "Physiotherapists", "Policymakers", "Product Managers", "Project Developers", "Project Managers", "Public Speakers", "Quantitative Traders & Developers", "Quality Assurance Teams", "Renewable Energy Investors", "Researchers", "Sales Professionals", "Security Engineers", "SEO Specialists", "Site Reliability Engineers", "Site Safety Officers", "Skincare Professionals", "Small Business Owners", "Small Contractors", "Small Landlords", "Social Media Managers", "Software Architects", "Software Developers", "Solo Attorneys", "Startup Founders", "Sustainability Officers", "System Administrators", "Team Managers", "Tradespeople", "Travel Agents", "UI/UX Designers", "UX Designers", "UX Researchers", "VCs", "Web3 Developers", "Webinar Hosts", "Wellness Coaches", "Writers"}
        B2C_SET = {"Affluent Solo Travelers", "Airbnb Hosts", "Career-Switchers", "Children", "Couples", "DeFi Users", "Digital Nomads", "Expatriates", "Families", "Family & Child Services", "Fitness Enthusiasts", "Frequent Travelers", "Friends", "General Consumers", "High School Students", "Honeymooners", "Individuals With Disorders", "Language Learners", "New Parents", "Parents", "Retail Crypto Investors", "Small Travel Groups", "Students", "Wellness-Conscious Consumers"}

        use_cases_to_process = UseCase.objects.all()
        updated_count = 0
        self.stdout.write(f"Processing {use_cases_to_process.count()} UseCases for backfilling...")
        for use_case in use_cases_to_process.iterator():
            market_names = set(use_case.target_markets.values_list('name', flat=True))
            original_model = use_case.business_model
            new_model = None
            if not market_names.isdisjoint(B2B_SET): new_model = 'B2B'
            elif not market_names.isdisjoint(PROSUMER_SET): new_model = 'Prosumer'
            elif not market_names.isdisjoint(B2C_SET): new_model = 'B2C'
            if new_model and new_model != original_model:
                use_case.business_model = new_model
                use_case.save(update_fields=['business_model'])
                updated_count += 1
        self.stdout.write(f"  Updated business_model for {updated_count} UseCases.")