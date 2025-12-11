import random
# rand_list = 

rand_list = [random.randint(1, 20) for _ in range(10)]

# list_comprehension_below_10 =

list_comprehension_below_10 = [num for num in rand_list if num < 10]

# list_comprehension_below_10 =

filter_below_10 = list(filter(lambda x:x < 10, rand_list))

# testing results

print('Random List:', rand_list)
print('Below 10 - List comprehension', list_comprehension_below_10)
print('Below 10 filter', filter_below_10)