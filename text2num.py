## Перевод прописной записи чисел в цифровую (ru-RU)
## автор библиотеки - Malakhov Vladimir

from fuzzywuzzy import fuzz

tokensExamp = [['ноль', "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять",
                "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать",
                "восемнадцать", "девятнадцать"],
               ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"],
               ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]]
thousendsTokens = ["квадриллион", "триллион", "миллиард", "миллион", "тысяч"]


def numInterpriter(text: str):
    moddedText = text
    sum = 0

    def unitsInterpriter(numsT: str):
        sumUnits = 0
        nums = numsT.split(' ')
        print(nums)
        for num in nums:
            rc = {'token': 0, 'percent': 0, 'dozen': 0}
            if fuzz.ratio('трех', num) != 100:
                for tokennum in range(len(tokensExamp)):
                    for i in range(len(tokensExamp[tokennum])):
                        vrt = fuzz.ratio(tokensExamp[tokennum][i], num)
                        if vrt > rc['percent'] and vrt > 50:
                            rc['percent'] = vrt
                            rc['token'] = i
                            rc['dozen'] = tokennum
            else:
                rc['token'] = 3
                rc['percent'] = 100

            sumUnits += rc['token'] * (10**rc['dozen'])
            print(rc)
        # print(sumUnits)
        return sumUnits


    for i in range(len(thousendsTokens)):
        if moddedText.find(thousendsTokens[i]) != -1:
            numsPart = moddedText.partition(thousendsTokens[i])
            print(numsPart)
            sum += unitsInterpriter(numsPart[0]) * (1000**(len(thousendsTokens)-i))

            moddedText = moddedText.replace(numsPart[0], "").split(' ', 1)[1]
            moddedText.strip()

    if moddedText:
        sum += unitsInterpriter(moddedText)

    return sum

if __name__ == '__main__':
    print(numInterpriter('две тысячи пятьдесят'))