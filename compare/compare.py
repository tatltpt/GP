import re

with open('/home/tuta/test/compare/real_label1.txt') as f1:
    file_1_text = f1.readlines()
  
with open('/home/tuta/test/compare/recognize_data1.txt') as f2:
    file_2_text = f2.readlines()

for l1 in file_1_text:
    for l2 in file_2_text:
        if (l1[:12] == l2[:12]):
            rex = '/[{}]/'.format(l1[12:])
            x = re.search(l1[12:], l2[12:])
            if x:
                print(l1[12:])
                print(l2[12:])
