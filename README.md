# OmniPing


I originally wrote OmniPing whilst testing a new Datacenter network for a customer. It proved useful and found some performance issues leading to improved configurations. Initially it was simply a CLI tool then became web-based to make management easier. Since then I decided to update it as it seemed like an ideal little project to help me learn about Python's Asyncio library. (The original version created Threads per task and was quite messy - hopefully this is less messy)

Imagine you're about to perform some kind of network change and you want to keep an eye on some critical devices. You could set up many terminals and run several pings or try and build a specificly filtered view using your network management tool. Or what if there is a re-occurring issue with a particular device that you want to be aware off but you don't trust your Monitoring team to let you know. Well OmniPing is an attempt to provide a light weight, easily deployable tool derived to help in some of these situations. 

OmniPing allows you to run some tailored tests either from your local machine or on a remote device (or container). The tests are either ping, http or https. You can also tailor the frequency of the tests and tweak some of the GUI parameters in order to distinguish between windows if you have multiple instances running.

