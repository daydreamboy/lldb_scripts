import lldb


def evaluateExpressionValue(expression, printError=True, language=lldb.eLanguageTypeC_plus_plus, tryAllThreads=False):
    frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
    options = lldb.SBExpressionOptions()
    options.SetLanguage(language)

    options.SetTrapExceptions(False)
    options.SetTimeoutInMicroSeconds(5000000)  # 5s
