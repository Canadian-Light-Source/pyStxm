
def load_dictionary(file_path):
    dictionary = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            dictionary[key.strip()] = value.strip()
    return dictionary

def search_and_replace(string, dictionary):
    for key, value in dictionary.items():
        string = string.replace(key, value)
    return string

# Example usage
file_path = "C:/controls/sandbox/branches/pyStxm3-76/cls/stylesheets/light_hires_disp/sub.txt"  # Replace with the path to your dictionary file
#input_string = 'Hello $name, today is $day.'
dictionary = load_dictionary(file_path)



output_string = search_and_replace(input_string, dictionary)
print(output_string)
#In this example, the load_dictionary()
