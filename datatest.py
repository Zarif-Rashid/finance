my_list = [
    {'id': 1, 'fruit': 'apple'},
    {'id': 2, 'fruit': 'banana'},
    {'id': 2, 'fruit': 'kiwi'},
]


for i in my_list:
    if i['id'] == 2:
        my_list.remove(i)

print(my_list)