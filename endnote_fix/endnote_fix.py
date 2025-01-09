#!/usr/bin/env python
import zipfile
import os
import re
from bs4 import BeautifulSoup
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Unpack the EPUB file and fix endnotes section numbering."
    )
    parser.add_argument("filename", type=str, help="The EPUB source file to unpack")
    parser.add_argument(
        "--repack", "-r", action="store_true", help="repack only, useful for debugging"
    )
    parser.add_argument(
        "--toc", "-t", action="store_true", help="modify toc only, useful for debugging"
    )
    args = parser.parse_args()
    return args


def append_fixed_to_filename(filename):
    name, ext = os.path.splitext(filename)
    fixed_filename = f"{name}_fixed{ext}"
    return fixed_filename


def extract_epub(epub_path, extract_to):
    with zipfile.ZipFile(epub_path, "r") as epub:
        epub.extractall(extract_to)


def fix_endnotes(soup):
    # 1. Find the <ol> element with the class "_idFootAndEndNoteOLAttrs"
    count = 0
    # Check if the ol element is found
    for ol_element in soup.find_all("ol"):
        # 2. Iterate over the <li> elements inside the <ol>
        for index, li_element in enumerate(ol_element.find_all("li"), start=1):
            # 3. For each <li> element, find the <a> element with class "_idEndnoteAnchor"
            a_element = li_element.find("a", class_="_idEndnoteAnchor")
            if a_element:
                # Find the <span> inside the <a> element
                span_element = a_element.find("span")
                if span_element and span_element.text == "-1":
                    # Set the text content of the <span> to the current index
                    span_element.string = str(index)
                    count += 1
    print("fixed endnotes: " + str(count))


def replace_end_ref_numbers(input_string):
    """
    Detects a string that ends with a series of numbers and removes the numbers.
    """
    corrected_string = re.sub(r"\d+$", "", input_string)
    return corrected_string


# NOTE: I realized this can be done in adobe indesign by just using the "layers" tab to remove empty text frames. but there are hundreds of pages to review
def remove_empty_frames(soup):
    # Find all <div> elements with class "Basic-Text-Frame"
    empty_frames = soup.find_all("div", class_="Basic-Text-Frame")

    count = 0
    # Iterate over each found <div> and check if it is empty
    for div in empty_frames:
        # If the div has no content (only whitespace), decompose it (remove it from the tree)
        if (
            not div.text.strip()  # and not div.contents # why does div.contents still return something? newline?
        ):  # Check both text and other elements inside the div
            div.decompose()  # Remove the empty <div>
            count += 1
    print("remove " + str(count) + " empty frames")


def modify_html_files(folder_path):
    # Walk through extracted files to find HTML files
    print("wrote modified html to:")
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".html") or file.endswith(".xhtml"):
                html_path = os.path.join(root, file)
                with open(html_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")
                fix_endnotes(soup)
                remove_empty_frames(soup)
                # Write changes back to the HTML file
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))
                print("  " + html_path)


def repack_epub(folder_path, output_epub):
    print("repack: " + folder_path)
    with zipfile.ZipFile(output_epub, "w", zipfile.ZIP_DEFLATED) as epub:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, folder_path)
                epub.write(full_path, relative_path)
                print("  " + full_path)
    print("result: " + output_epub)


CHAPTER_NUMBERS = [
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "ELEVEN",
    "TWELVE",
    "THIRTEEN",
    "FOURTEEN",
    "FIFTEEN",
    "SIXTEEN",
    "SEVENTEEN",
    "EIGHTEEN",
    "NINETEEN",
]


def __modify_toc_ncx(soup):
    count = 0
    found_chapter_one = False
    found_endnotes = False

    # Check if the navMap element is found
    for navmap_element in soup.find_all("navmap"):
        # 2. Iterate over the <navPoint> elements inside the <ol>
        for index, navpoint_element in enumerate(
            navmap_element.find_all("navpoint"), start=1
        ):
            # 3. For each <navPoint> element, change the text to include the chaptr number
            text_element = navpoint_element.find("text")
            if text_element.text == "Endnotes":
                found_endnotes = True
                break  # exit after finding endnotes.
            if text_element.text == "Darian":
                found_chapter_one = True  # start after finding darian (chapter one)
                print("modify_toc: found chapter one")
            if found_chapter_one:
                if count >= len(CHAPTER_NUMBERS):
                    print("ERROR: modify_toc iterated to chapter: " + str(count))
                    break
                # MODIFY the TOC chapter title to include numbers.
                text_element.string = CHAPTER_NUMBERS[count] + " " + text_element.text

                # NOTE: Eating for Two and Meeting his BFF have numbers at the end (endnote reference)
                # we want these to show up in the book but not in the TOC section metadata.
                # so we scrub it out here.
                text_element.string = replace_end_ref_numbers(text_element.string)

                count += 1
        if found_endnotes:
            break

    print("__modify_toc_ncx: " + str(count))


def __modify_toc_xhtml(soup):
    count = 0
    found_chapter_one = False
    found_endnotes = False

    # Check if the navMap element is found
    for ol_element in soup.find_all("ol"):
        # 2. Iterate over the <navPoint> elements inside the <ol>
        for index, li_element in enumerate(ol_element.find_all("li"), start=1):
            # 3. For each <navPoint> element, change the text to include the chaptr number
            a_element = li_element.find("a")
            if a_element.text == "Endnotes":
                found_endnotes = True
                break  # exit after finding endnotes.
            if a_element.text == "Darian":
                found_chapter_one = True  # start after finding darian (chapter one)
                print("modify_toc: found chapter one")
            if found_chapter_one:
                if count >= len(CHAPTER_NUMBERS):
                    print("ERROR: modify_toc iterated to chapter: " + str(count))
                    break
                # MODIFY the TOC chapter title to include numbers.
                a_element.string = CHAPTER_NUMBERS[count] + " " + a_element.text
                # NOTE: Eating for Two and Meeting his BFF have numbers at the end (endnote reference)
                # we want these to show up in the book but not in the TOC section metadata.
                # so we scrub it out here.
                a_element.string = replace_end_ref_numbers(a_element.string)
                count += 1
        if found_endnotes:
            break
    print("__modify_toc_xhtml: " + str(count))


def __modify_toc_content(soup):
    count = 0
    found_chapter_one = False
    found_endnotes = False

    # Check if the toc container element is found
    for div_element in soup.find_all("div", {"epub:type": "toc"}):
        print("found div")
        # 2. Iterate over the <h1> elements inside the <div>
        for index, h1_element in enumerate(div_element.find_all("h1"), start=1):
            # 3. For each <h1> element, change the text to include the chaptr number
            a_element = h1_element.find("a")
            if not a_element:
                continue
            # sometimes the chapter title is inside a spasn
            optional_span = a_element.find("span")
            if optional_span:
                a_element = optional_span
            if a_element.text == "Endnotes":
                found_endnotes = True
                break  # exit after finding endnotes.
            if a_element.text == "Darian":
                found_chapter_one = True  # start after finding darian (chapter one)
                print("__modify_toc_content: found chapter one")
            if found_chapter_one:
                if count >= len(CHAPTER_NUMBERS):
                    print("ERROR: modify_toc iterated to chapter: " + str(count))
                    break
                # MODIFY the TOC chapter title to include numbers.
                a_element.string = CHAPTER_NUMBERS[count] + " " + a_element.text
                # NOTE: Eating for Two and Meeting his BFF have numbers at the end (endnote reference)
                # we want these to show up in the book but not in the TOC section metadata.
                # so we scrub it out here.
                a_element.string = replace_end_ref_numbers(a_element.string)
                count += 1
        if found_endnotes:
            break
    print("__modify_toc_content: " + str(count))


def modify_toc(folder_path):
    # Walk through extracted files to find TOC files
    print("wrote modified toc to:")
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.startswith("toc"):
                toc_path = os.path.join(root, file)
                with open(toc_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")

                __modify_toc_ncx(soup)
                __modify_toc_xhtml(soup)

                # Write changes back to the TOC file
                with open(toc_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))
                print("  " + toc_path)
            else:
                toc_path = os.path.join(root, file)
                if toc_path.endswith("xhtml"):
                    with open(toc_path, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f, "html.parser")

                    __modify_toc_content(soup)

                    # Write changes back to the TOC file
                    with open(toc_path, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                    print("  " + toc_path)


def main():
    args = parse_args()

    # Usage
    epub_file = args.filename
    extract_folder = "endnote_fix_temp"
    output_epub = append_fixed_to_filename(epub_file)

    # MODIFY TOC ONLY
    if args.toc:
        modify_toc(extract_folder)
        print("Completed TOC MODIFY ONLY.")
        return

    # REPACK ONLY
    if args.repack:
        repack_epub(extract_folder, output_epub)
        print("Completed REPACK ONLY.")
        return

    # Step 1: Extract the EPUB
    extract_epub(epub_file, extract_folder)

    # Step 2: Modify the HTML files
    modify_html_files(extract_folder)

    # Step 3: Modify TOC files
    modify_toc(extract_folder)

    # Step 4: Repack the EPUB
    repack_epub(extract_folder, output_epub)

    print("EPUB modification complete.")


if __name__ == "__main__":
    main()
