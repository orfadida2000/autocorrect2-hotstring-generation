import json

from multypo import get_supported_languages, register_keyboard_layout


def main():
    # Get the list of supported languages from the multypo package

    custom_keyboard = [
        list("qwertyuiop"),
        list("asdfghjkl"),
        list("zxcvbnm"),
    ]

    register_keyboard_layout(
        lang_code="en-custom",
        language="english-custom",
        keyboard_rows=custom_keyboard,
        left_keys=list("qwertasdfgzxcvb"),
        right_keys=list("yuiophjklbnm"),
        ignoring_set={"million", "billion", "42"},
    )

    supported_languages = get_supported_languages()

    json_output = json.dumps(supported_languages, indent=2)
    print(json_output)


if __name__ == "__main__":
    main()
