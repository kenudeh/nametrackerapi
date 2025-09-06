from pathlib import Path
from django.core.management import call_command
from django.db import transaction
from django.conf import settings
from datetime import date
from django.utils import timezone

#Imports for syllables counting
import pyphen
import nltk



def process_file(file_record):
    """Shared processing logic"""
    file_path = Path(settings.UPLOAD_DIR) / file_record.filename
    with transaction.atomic():
        call_command(
            "load_json",
            str(file_path),
            "--drop_date", str(file_record.drop_date),
            "--domain_list", file_record.domain_list
        )
        file_record.processed = True
        file_record.processed_at = timezone.now()
        file_record.save()




# --- Setup for Syllable Counting ---
try:
    # Attempt to load the CMU Pronouncing Dictionary
    arpabet = nltk.corpus.cmudict.dict()
except LookupError:
    # If not downloaded, download it. This is a fallback for deployment.
    nltk.download('cmudict')
    arpabet = nltk.corpus.cmudict.dict()

# Initialize Pyphen for US English
pyphen_dic = pyphen.Pyphen(lang='en_US')



def count_syllables_hybrid(word):
    """
    Counts syllables using a hybrid dictionary-first, rule-based-fallback approach.
    """
    word = word.lower()
    if not word:
        return 0

     # 1. Try the dictionary-based approach first (most accurate)   
    try:
        # Count the number of phonemes that are vowels (end in a digit)
        return [len(list(y for y in x if y[-1].isdigit())) for x in arpabet[word]][0]
    except KeyError:
        # 2. If word not in dictionary, fall back to Pyphen
        # This inserts hyphens and we count the parts.
        hyphenated = pyphen_dic.inserted(word)
        return len(hyphenated.split('-'))