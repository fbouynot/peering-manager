import json
import re
import subprocess

from django.conf import settings


def call_irr_as_set_resolver(irr_as_set, address_family=6):
    """
    Call a subprocess to expand the given AS-SET for an IP version.
    """
    prefixes = []

    if not irr_as_set:
        return prefixes

    # Call bgpq3 with arguments to get a JSON result
    command = [
        settings.BGPQ3_PATH,
        "-h",
        settings.BGPQ3_HOST,
        "-S",
        settings.BGPQ3_SOURCES,
        f"-{address_family}",
        "-A",
        "-j",
        "-l",
        "prefix_list",
        irr_as_set,
    ]

    # Merge user settings to command line right before the name of the prefix list
    if settings.BGPQ3_ARGS:
        index = len(command) - 3
        command[index:index] = settings.BGPQ3_ARGS[
            "ipv6" if address_family == 6 else "ipv4"
        ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    if process.returncode != 0:
        error_log = f"{settings.BGPQ3_PATH} exit code is {process.returncode}"
        if err and err.strip():
            error_log += f", stderr: {err}"
        raise ValueError(error_log)

    prefixes.extend(list(json.loads(out.decode())["prefix_list"]))

    return prefixes


def parse_irr_as_set(asn, irr_as_set):
    """
    Validate that an AS-SET is usable and split it into smaller part if it is actually
    composed of several AS-SETs.
    """
    as_sets = []

    # Can't work with empty or whitespace only AS-SET
    if not irr_as_set or not irr_as_set.strip():
        return [f"AS{asn}"]

    unparsed = re.split(r"[/,&\s]", irr_as_set)
    for element in unparsed:
        value = element.strip()

        if not value:
            continue

        for regexp in [
            # Remove registry prefix if any
            r"^(?:{}):[:\s]".format(settings.BGPQ3_SOURCES.replace(",", "|")),
            # Removing "ipv4:" and "ipv6:"
            r"^(?:ipv4|ipv6):",
        ]:
            pattern = re.compile(regexp, flags=re.IGNORECASE)
            value, number_of_subs_made = pattern.subn("", value)
            # If some substitutions have been made, make sure to clean things up
            if number_of_subs_made > 0:
                value = value.strip()

        as_sets.append(value)

    return as_sets
